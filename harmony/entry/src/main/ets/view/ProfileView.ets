/**
 * 我的：账号、功能入口、服务器信息。
 *
 * 「服务器地址」常驻可见——自托管用户换域名、换端口是常态，
 * 藏在三级菜单里只会增加求助量。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { StatsSummary } from '../common/Models';
import { Prefs } from '../common/Prefs';
import { Theme } from '../common/Theme';
import { toast, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { Card, SectionTitle, SettingRow } from './Common';

@Component
export struct ProfileView {
  @Link @Watch('onRefreshKeyChange') refreshKey: number;

  @State private username: string = '';
  @State private serverUrl: string = '';
  @State private stats: StatsSummary | null = null;
  @State private feedPath: string = '';

  aboutToAppear(): void {
    this.username = Prefs.username();
    this.serverUrl = Prefs.serverUrl();
    this.feedPath = Prefs.feedPath();
    this.load();
  }

  onRefreshKeyChange(): void {
    this.username = Prefs.username();
    this.serverUrl = Prefs.serverUrl();
    this.feedPath = Prefs.feedPath();
    this.load();
  }

  private async load(): Promise<void> {
    try {
      this.stats = await Api.statsSummary();
    } catch (e) {
      // 概览失败不影响入口可用性
    }
  }

  private async confirmLogout(): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '退出登录',
        message: '将清除本机令牌与本地提醒，数据仍保存在服务器上。',
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '退出', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await AppStore.logout();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  private async syncReminders(): Promise<void> {
    try {
      const n: number = await AppStore.syncReminders();
      toast(`已排入 ${n} 条本地提醒`);
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Scroll() {
      Column({ space: Theme.GAP }) {
        // -------- 账号卡 --------
        Card({
          content: () => {
            this.accountCard();
          },
        });

        // -------- 概览 --------
        if (this.stats) {
          Card({
            content: () => {
              this.statsCard();
            },
          });
        }

        // -------- 功能入口 --------
        Card({
          content: () => {
            this.entriesCard();
          },
        });

        // -------- 数据与同步 --------
        Card({
          content: () => {
            this.dataCard();
          },
        });

        Button('退出登录')
          .width('100%')
          .height(44)
          .borderRadius(12)
          .backgroundColor('#FEE2E2')
          .fontColor(Theme.DANGER)
          .onClick(() => {
            this.confirmLogout();
          });

        Text('抵达 Reach · 鸿蒙端')
          .fontSize(11)
          .fontColor(Theme.TEXT_WEAK)
          .padding({ top: 6, bottom: 18 });
      }
      .width('100%')
      .padding({ left: Theme.PAGE_PADDING, right: Theme.PAGE_PADDING, top: 12 });
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG)
    .scrollBar(BarState.Off);
  }

  @Builder
  accountCard() {
    Row({ space: 12 }) {
      Text(this.username.length > 0 ? this.username.substring(0, 1).toUpperCase() : '?')
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
        .fontColor('#FFFFFF')
        .width(50)
        .height(50)
        .textAlign(TextAlign.Center)
        .backgroundColor(Theme.BRAND)
        .borderRadius(25);
      Column({ space: 4 }) {
        Text(this.username.length > 0 ? this.username : '未登录')
          .fontSize(17)
          .fontWeight(FontWeight.Medium)
          .fontColor(Theme.TEXT);
        Text(this.serverUrl.length > 0 ? this.serverUrl : '未配置服务器')
          .fontSize(11)
          .fontColor(Theme.TEXT_SUB)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis });
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1);
    }
    .width('100%');
  }

  @Builder
  statsCard() {
    Column({ space: 8 }) {
      SectionTitle({
        title: '概览',
        action: '周回顾',
        onAction: () => {
          router.pushUrl({ url: 'pages/StatsPage' });
        },
      });
      Row() {
        this.statCell('待办', `${this.stats!.total_todo}`);
        this.statCell('已完成', `${this.stats!.total_done}`);
        this.statCell('连续', `${this.stats!.streak}天`);
        this.statCell('今日专注', `${this.stats!.focus_minutes_today}分`);
      }
      .width('100%');
    }
    .width('100%');
  }

  @Builder
  statCell(label: string, value: string) {
    Column({ space: 3 }) {
      Text(value).fontSize(16).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT);
      Text(label).fontSize(11).fontColor(Theme.TEXT_SUB);
    }
    .layoutWeight(1);
  }

  @Builder
  entriesCard() {
    Column({ space: 0 }) {
      SectionTitle({ title: '功能' });
      SettingRow({
        label: '目标管理',
        value: '拆解长期目标',
        onTap: () => {
          router.pushUrl({ url: 'pages/GoalsPage' });
        },
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '四象限',
        value: '重要 × 紧急',
        onTap: () => {
          router.pushUrl({ url: 'pages/MatrixPage' });
        },
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '专注',
        value: `${AppStore.settings().focusMinutes} 分钟`,
        onTap: () => {
          router.pushUrl({ url: 'pages/FocusPage' });
        },
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '标签管理',
        value: `${AppStore.tags().length} 个`,
        onTap: () => {
          router.pushUrl({ url: 'pages/TagsPage' });
        },
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '回收站',
        value: '可恢复已删除',
        onTap: () => {
          router.pushUrl({ url: 'pages/TrashPage' });
        },
      });
    }
    .width('100%');
  }

  @Builder
  dataCard() {
    Column({ space: 0 }) {
      SectionTitle({ title: '设置与同步' });
      SettingRow({
        label: '偏好设置',
        value: '云端同步',
        onTap: () => {
          router.pushUrl({ url: 'pages/SettingsPage' });
        },
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '重排本地提醒',
        value: AppStore.settings().localReminderEnabled ? '已开启' : '已关闭',
        showArrow: false,
        onTap: () => {
          this.syncReminders();
        },
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '日历订阅地址',
        value: this.feedPath.length > 0 ? '点击查看' : '未生成',
        onTap: () => {
          this.showFeed();
        },
      });
    }
    .width('100%');
  }

  private showFeed(): void {
    if (this.feedPath.length === 0) {
      toast('请先在偏好设置中同步一次');
      return;
    }
    promptAction.showDialog({
      title: '日历订阅（ICS）',
      message: `${this.serverUrl}${this.feedPath}\n\n把该地址添加到系统日历 / 其他日历应用，即可只读订阅任务到期日。地址含私密令牌，请勿公开分享。`,
      buttons: [{ text: '知道了', color: Theme.BRAND }],
    }).catch(() => {
    });
  }
}
