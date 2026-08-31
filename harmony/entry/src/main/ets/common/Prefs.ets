/**
 * 本地持久化（AppStorage + PersistentStorage）。
 *
 * 只持久化「重启后必须还在」的少量键：服务器地址、令牌、用户名、偏好快照。
 * 业务数据一律不落地——自托管场景服务端就是唯一真相源，本地缓存业务数据
 * 只会引入「离线改了但同步冲突」这类远超收益的复杂度。
 *
 * 偏好用 JSON 字符串整体存取而不是逐键 persistProp：偏好键会随版本增长，
 * 整体存取可让「后端新增一个键」在客户端零改动生效。
 */
import { AppSettings, DEFAULT_SETTINGS } from './Models';

export const KEY_SERVER_URL: string = 'reach_server_url';
export const KEY_TOKEN: string = 'reach_token';
export const KEY_USERNAME: string = 'reach_username';
export const KEY_SETTINGS: string = 'reach_settings';
export const KEY_FEED_PATH: string = 'reach_feed_path';
export const KEY_PUSH_TOKEN: string = 'reach_push_token';

/** 默认指向本机开发服务器；模拟器访问宿主机请改成宿主机局域网 IP。 */
const DEFAULT_SERVER_URL: string = 'http://127.0.0.1:8000';

export class Prefs {
  /** 必须在 EntryAbility.onCreate 里调用一次，早于任何页面构建。 */
  static init(): void {
    PersistentStorage.persistProp<string>(KEY_SERVER_URL, DEFAULT_SERVER_URL);
    PersistentStorage.persistProp<string>(KEY_TOKEN, '');
    PersistentStorage.persistProp<string>(KEY_USERNAME, '');
    PersistentStorage.persistProp<string>(KEY_SETTINGS, '');
    PersistentStorage.persistProp<string>(KEY_FEED_PATH, '');
    PersistentStorage.persistProp<string>(KEY_PUSH_TOKEN, '');
  }

  private static str(key: string): string {
    const v: string | undefined = AppStorage.get<string>(key);
    return v === undefined || v === null ? '' : v;
  }

  /** 归一化后的服务器地址：补协议、去掉结尾斜杠，避免拼出 `//api/tasks`。 */
  static serverUrl(): string {
    let raw: string = Prefs.str(KEY_SERVER_URL).trim();
    if (!raw) {
      return '';
    }
    if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
      raw = 'https://' + raw;
    }
    while (raw.endsWith('/')) {
      raw = raw.substring(0, raw.length - 1);
    }
    return raw;
  }

  static setServerUrl(url: string): void {
    AppStorage.setOrCreate<string>(KEY_SERVER_URL, url);
  }

  static token(): string {
    return Prefs.str(KEY_TOKEN);
  }

  static setToken(token: string): void {
    AppStorage.setOrCreate<string>(KEY_TOKEN, token);
  }

  static username(): string {
    return Prefs.str(KEY_USERNAME);
  }

  static setUsername(name: string): void {
    AppStorage.setOrCreate<string>(KEY_USERNAME, name);
  }

  static feedPath(): string {
    return Prefs.str(KEY_FEED_PATH);
  }

  static setFeedPath(p: string): void {
    AppStorage.setOrCreate<string>(KEY_FEED_PATH, p);
  }

  static pushToken(): string {
    return Prefs.str(KEY_PUSH_TOKEN);
  }

  static setPushToken(t: string): void {
    AppStorage.setOrCreate<string>(KEY_PUSH_TOKEN, t);
  }

  /**
   * 读取偏好快照。
   *
   * 解析失败（旧版本残留脏数据、手工篡改）时静默回退到默认值：
   * 偏好损坏绝不能让应用起不来。
   */
  static settings(): AppSettings {
    const raw: string = Prefs.str(KEY_SETTINGS);
    if (!raw) {
      return DEFAULT_SETTINGS;
    }
    try {
      const parsed = JSON.parse(raw) as AppSettings;
      // 与默认值合并：后端新增键、本地快照较老时不会读到 undefined
      return Prefs.mergeSettings(DEFAULT_SETTINGS, parsed);
    } catch (e) {
      return DEFAULT_SETTINGS;
    }
  }

  static setSettings(s: AppSettings): void {
    AppStorage.setOrCreate<string>(KEY_SETTINGS, JSON.stringify(s));
  }

  /** 逐字段兜底合并：ArkTS 无对象展开运算符，显式列出反而更安全。 */
  static mergeSettings(base: AppSettings, patch: AppSettings): AppSettings {
    return {
      focusMinutes: patch.focusMinutes ?? base.focusMinutes,
      focusBreakMinutes: patch.focusBreakMinutes ?? base.focusBreakMinutes,
      weekStart: patch.weekStart ?? base.weekStart,
      timezone: patch.timezone ?? base.timezone,
      theme: patch.theme ?? base.theme,
      accentColor: patch.accentColor ?? base.accentColor,
      lunarSource: patch.lunarSource ?? base.lunarSource,
      lunarApiBase: patch.lunarApiBase ?? base.lunarApiBase,
      holidayApiBase: patch.holidayApiBase ?? base.holidayApiBase,
      lunarApiKey: patch.lunarApiKey ?? base.lunarApiKey,
      defaultRemindBeforeMinutes:
        patch.defaultRemindBeforeMinutes ?? base.defaultRemindBeforeMinutes,
      localReminderEnabled: patch.localReminderEnabled ?? base.localReminderEnabled,
      showCompleted: patch.showCompleted ?? base.showCompleted,
      defaultView: patch.defaultView ?? base.defaultView,
    };
  }

  /** 退出登录：清令牌与派生信息，保留服务器地址（下次登录不用重填）。 */
  static clearSession(): void {
    Prefs.setToken('');
    Prefs.setUsername('');
    Prefs.setFeedPath('');
  }
}
