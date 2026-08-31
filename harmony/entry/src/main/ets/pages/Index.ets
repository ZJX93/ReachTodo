/**
 * 根页面：登录门禁 + 底部 Tab。
 *
 * 用 `@StorageLink` 直接监听持久化的 token，而不是 router 跳转到独立登录页：
 * 令牌可能在任意时刻由 401 拦截器清空（后台请求失败、服务端重签密钥），
 * 「状态驱动」能保证任何路径下都立刻回到登录态，而 router 方案会漏掉
 * 从深层页面触发 401 的场景。
 */
import { KEY_TOKEN } from '../common/Prefs';
import { Theme } from '../common/Theme';
import { AppStore } from '../stores/AppStore';
import { CalendarView } from '../view/CalendarView';
import { DashboardView } from '../view/DashboardView';
import { LoginView } from '../view/LoginView';
import { ProfileView } from '../view/ProfileView';
import { RecordsView } from '../view/RecordsView';
import { TasksView } from '../view/TasksView';

interface TabDef {
  key: string;
  label: string;
  icon: string;
}

const TABS: TabDef[] = [
  { key: 'dashboard', label: '看板', icon: '◉' },
  { key: 'tasks', label: '任务', icon: '☰' },
  { key: 'calendar', label: '日历', icon: '▦' },
  { key: 'records', label: '记录', icon: '✎' },
  { key: 'profile', label: '我的', icon: '☺' },
];

@Entry
@Component
struct Index {
  @StorageLink(KEY_TOKEN) token: string = '';
  @State private index: number = 0;

  /**
   * 每个 Tab 一个刷新计数器。
   * 切回某个 Tab 或从编辑页返回时只自增「当前 Tab」的计数，
   * 避免一次返回触发 5 个页面同时发请求。
   */
  @State private keyDashboard: number = 0;
  @State private keyTasks: number = 0;
  @State private keyCalendar: number = 0;
  @State private keyRecords: number = 0;
  @State private keyProfile: number = 0;

  private booted: boolean = false;

  aboutToAppear(): void {
    this.applyDefaultView();
    this.bootIfNeeded();
  }

  /** 从编辑页 / 二级页返回时刷新当前 Tab。 */
  onPageShow(): void {
    this.bootIfNeeded();
    if (this.token.length > 0) {
      this.bumpCurrent();
    }
  }

  /**
   * 冷启动时若已有令牌，补做一次初始化（拉偏好、维度、标签、排提醒）。
   * `booted` 保证只做一次，避免每次 onPageShow 都重复。
   */
  private bootIfNeeded(): void {
    if (this.booted || this.token.length === 0) {
      return;
    }
    this.booted = true;
    AppStore.bootstrap().catch(() => {
    });
  }

  /** 按偏好里的「默认视图」决定首屏落在哪个 Tab。 */
  private applyDefaultView(): void {
    const target: string = AppStore.settings().defaultView;
    for (let i = 0; i < TABS.length; i++) {
      if (TABS[i].key === target) {
        this.index = i;
        return;
      }
    }
    // matrix / goals 等非 Tab 视图统一落回看板，看板上有它们的入口
    this.index = 0;
  }

  private bumpCurrent(): void {
    if (this.index === 0) {
      this.keyDashboard = this.keyDashboard + 1;
    } else if (this.index === 1) {
      this.keyTasks = this.keyTasks + 1;
    } else if (this.index === 2) {
      this.keyCalendar = this.keyCalendar + 1;
    } else if (this.index === 3) {
      this.keyRecords = this.keyRecords + 1;
    } else {
      this.keyProfile = this.keyProfile + 1;
    }
  }

  build() {
    Column() {
      if (this.token.length === 0) {
        LoginView();
      } else {
        Tabs({ barPosition: BarPosition.End, index: this.index }) {
          TabContent() {
            DashboardView({ refreshKey: $keyDashboard });
          }
          .tabBar(this.bottomItem(0));

          TabContent() {
            TasksView({ refreshKey: $keyTasks });
          }
          .tabBar(this.bottomItem(1));

          TabContent() {
            CalendarView({ refreshKey: $keyCalendar });
          }
          .tabBar(this.bottomItem(2));

          TabContent() {
            RecordsView({ refreshKey: $keyRecords });
          }
          .tabBar(this.bottomItem(3));

          TabContent() {
            ProfileView({ refreshKey: $keyProfile });
          }
          .tabBar(this.bottomItem(4));
        }
        .barHeight(58)
        .animationDuration(150)
        .onChange((i: number) => {
          this.index = i;
          this.bumpCurrent();
        })
        .width('100%')
        .height('100%');
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  bottomItem(i: number) {
    Column({ space: 2 }) {
      Text(TABS[i].icon)
        .fontSize(19)
        .fontColor(this.index === i ? Theme.BRAND : Theme.TEXT_WEAK);
      Text(TABS[i].label)
        .fontSize(11)
        .fontColor(this.index === i ? Theme.BRAND : Theme.TEXT_WEAK);
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center);
  }
}
