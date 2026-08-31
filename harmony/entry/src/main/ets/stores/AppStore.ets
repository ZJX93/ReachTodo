/**
 * 会话与全局缓存。
 *
 * 只缓存「几乎不变、但每个页面都要用」的三类数据：偏好、维度、标签。
 * 任务 / 记录等业务数据一律由页面按需拉取，不进这里——把可变数据塞进全局单例，
 * 迟早会出现「A 页改了 B 页没刷新」的脏读，而它的收益（省几次请求）微不足道。
 */
import common from '@ohos.app.ability.common';
import { Api, settingsToPatch } from '../common/Api';
import { ApiClient } from '../common/ApiClient';
import {
  AppSettings,
  CategoryOut,
  SettingsOut,
  SettingsPatch,
  TagOut,
  TaskOut,
  TokenOut,
  UserCreate,
} from '../common/Models';
import { Prefs } from '../common/Prefs';
import { Push } from '../common/Push';
import { Reminder } from '../common/Reminder';

class AppStoreClass {
  private categoryCache: CategoryOut[] = [];
  private tagCache: TagOut[] = [];
  private abilityContext: common.UIAbilityContext | null = null;

  // ------------------------------------------------------------ 生命周期
  attachContext(context: common.UIAbilityContext): void {
    this.abilityContext = context;
  }

  /** 注册 401 处理器：令牌失效时清会话，UI 通过 token 变化自动回登录页。 */
  installUnauthorizedHandler(): void {
    ApiClient.setUnauthorizedHandler(() => {
      this.categoryCache = [];
      this.tagCache = [];
      Prefs.clearSession();
    });
  }

  isLoggedIn(): boolean {
    return Prefs.token().length > 0;
  }

  // ------------------------------------------------------------ 认证
  async login(username: string, password: string): Promise<void> {
    const body: UserCreate = { username: username, password: password };
    const res: TokenOut = await Api.login(body);
    this.acceptToken(res, username);
  }

  async register(username: string, password: string, email: string): Promise<void> {
    const body: UserCreate = {
      username: username,
      password: password,
      email: email.length > 0 ? email : null,
    };
    const res: TokenOut = await Api.register(body);
    this.acceptToken(res, username);
  }

  private acceptToken(res: TokenOut, fallbackName: string): void {
    if (!res.access_token || res.access_token.length === 0) {
      throw new Error('服务器未返回登录令牌');
    }
    Prefs.setToken(res.access_token);
    Prefs.setUsername(res.user?.username ?? fallbackName);
  }

  /**
   * 登录后的初始化。
   *
   * 每一步都独立 try/catch：任何一步失败（例如设备没有推送服务）都不能阻断
   * 其余步骤，更不能让用户卡在登录页。
   */
  async bootstrap(): Promise<void> {
    try {
      await this.loadSettings();
    } catch (e) {
    }
    try {
      await this.loadCategories(true);
    } catch (e) {
    }
    try {
      await this.loadTags(true);
    } catch (e) {
    }
    if (this.abilityContext) {
      await Reminder.ensureNotificationPermission(this.abilityContext);
    }
    try {
      await this.syncReminders();
    } catch (e) {
    }
    try {
      await Push.register('HarmonyOS');
    } catch (e) {
    }
  }

  async logout(): Promise<void> {
    await Push.unregister();
    await Reminder.cancelAll();
    this.categoryCache = [];
    this.tagCache = [];
    Prefs.clearSession();
  }

  // ------------------------------------------------------------ 偏好
  /** 从服务端拉取偏好并落地为本地快照（服务端是唯一真相源）。 */
  async loadSettings(): Promise<AppSettings> {
    const res: SettingsOut = await Api.settings();
    const merged: AppSettings = Prefs.mergeSettings(Prefs.settings(), res.settings);
    Prefs.setSettings(merged);
    Prefs.setFeedPath(res.feed_path ?? '');
    return merged;
  }

  /** 本地偏好（无网络时也可用）。 */
  settings(): AppSettings {
    return Prefs.settings();
  }

  /**
   * 保存偏好：先写服务端再落本地。
   *
   * 顺序很关键——若先写本地再失败，用户会看到「改了但换个设备没生效」，
   * 比直接报错更难理解。
   */
  async saveSettings(patch: SettingsPatch): Promise<AppSettings> {
    const res: SettingsOut = await Api.saveSettings(patch);
    const merged: AppSettings = Prefs.mergeSettings(Prefs.settings(), res.settings);
    Prefs.setSettings(merged);
    Prefs.setFeedPath(res.feed_path ?? '');
    return merged;
  }

  /** 整份覆盖（设置页「保存」按钮用）。 */
  async saveAllSettings(s: AppSettings): Promise<AppSettings> {
    return await this.saveSettings(settingsToPatch(s));
  }

  // ------------------------------------------------------------ 维度 / 标签
  async loadCategories(force: boolean = false): Promise<CategoryOut[]> {
    if (!force && this.categoryCache.length > 0) {
      return this.categoryCache;
    }
    this.categoryCache = await Api.categories();
    return this.categoryCache;
  }

  categories(): CategoryOut[] {
    return this.categoryCache;
  }

  categoryName(id: number): string {
    for (const c of this.categoryCache) {
      if (c.id === id) {
        return c.name;
      }
    }
    return '';
  }

  async loadTags(force: boolean = false): Promise<TagOut[]> {
    if (!force && this.tagCache.length > 0) {
      return this.tagCache;
    }
    this.tagCache = await Api.tags();
    return this.tagCache;
  }

  tags(): TagOut[] {
    return this.tagCache;
  }

  /** 标签名 → 颜色（列表里给标签上色，避免每个标签都去查接口）。 */
  tagColor(name: string): string {
    for (const t of this.tagCache) {
      if (t.name === name) {
        return t.color;
      }
    }
    return '#9CA3AF';
  }

  // ------------------------------------------------------------ 提醒
  /**
   * 重排本地提醒。
   *
   * 只拉「未完成且已排期」的任务，按到期日升序取前若干条，
   * 避免把几百条任务全量拉回来只为了排 28 条提醒。
   */
  async syncReminders(): Promise<number> {
    if (!this.isLoggedIn()) {
      return 0;
    }
    const tasks: TaskOut[] = await Api.tasks({
      status: 'todo',
      sort: 'due',
      limit: 200,
    });
    const dated: TaskOut[] = tasks.filter((t: TaskOut) => !!t.due_date);
    return await Reminder.sync(dated, this.settings());
  }
}

export const AppStore: AppStoreClass = new AppStoreClass();
