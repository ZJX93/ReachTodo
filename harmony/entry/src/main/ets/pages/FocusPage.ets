/**
 * 专注计时（番茄钟）。
 *
 * 只在**一次专注真正完成**时才上报 `/api/focus`。中途放弃不上报，
 * 否则统计里的「专注时长」会被大量 2 分钟的碎片污染，失去参考价值。
 *
 * 计时用「目标结束时间戳」而不是「每秒累加计数」：定时器在后台可能被降频，
 * 累加法会越走越慢，而基于时间戳的算法回到前台后能自动对齐真实时间。
 */
import router from '@ohos.router';
import { Api } from '../common/Api';
import { TaskOut } from '../common/Models';
import { Theme } from '../common/Theme';
import { toast, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { Card, NavBar, SectionTitle } from '../view/Common';

@Entry
@Component
struct FocusPage {
  @State private totalMinutes: number = 25;
  @State private breakMinutes: number = 5;
  @State private remainSec: number = 0;
  @State private running: boolean = false;
  @State private onBreak: boolean = false;
  @State private completed: number = 0;
  @State private tasks: TaskOut[] = [];
  @State private boundTaskId: number = 0;

  private timerId: number = -1;
  private endAt: number = 0;

  aboutToAppear(): void {
    const s = AppStore.settings();
    this.totalMinutes = s.focusMinutes;
    this.breakMinutes = s.focusBreakMinutes;
    this.remainSec = this.totalMinutes * 60;
    this.loadTasks();
  }

  aboutToDisappear(): void {
    this.clearTimer();
  }

  private async loadTasks(): Promise<void> {
    try {
      this.tasks = await Api.tasks({ status: 'todo', sort: 'priority', limit: 30 });
    } catch (e) {
      // 绑定任务是可选的
    }
  }

  private clearTimer(): void {
    if (this.timerId !== -1) {
      clearInterval(this.timerId);
      this.timerId = -1;
    }
  }

  private start(): void {
    if (this.running) {
      return;
    }
    this.endAt = Date.now() + this.remainSec * 1000;
    this.running = true;
    this.timerId = setInterval(() => {
      const left: number = Math.round((this.endAt - Date.now()) / 1000);
      if (left <= 0) {
        this.remainSec = 0;
        this.finish();
      } else {
        this.remainSec = left;
      }
    }, 500);
  }

  private pause(): void {
    this.clearTimer();
    this.running = false;
  }

  private reset(): void {
    this.clearTimer();
    this.running = false;
    this.onBreak = false;
    this.remainSec = this.totalMinutes * 60;
  }

  /** 一段结束：专注段上报并切到休息，休息段结束后切回专注。 */
  private finish(): void {
    this.clearTimer();
    this.running = false;
    if (this.onBreak) {
      this.onBreak = false;
      this.remainSec = this.totalMinutes * 60;
      toast('休息结束，可以开始下一段专注');
      return;
    }
    this.completed = this.completed + 1;
    this.report(this.totalMinutes);
    this.onBreak = true;
    this.remainSec = this.breakMinutes * 60;
    toast(`完成 ${this.totalMinutes} 分钟专注，去休息一下`);
  }

  private async report(minutes: number): Promise<void> {
    try {
      await Api.createFocus({
        minutes: minutes,
        task_id: this.boundTaskId > 0 ? this.boundTaskId : null,
      });
    } catch (err) {
      // 上报失败不回滚本地计数：用户确实专注了，不该因为网络问题被否定
      toastError(err as object);
    }
  }

  /** 提前结束但已专注足够久（≥5 分钟）时按实际时长记账。 */
  private async stopAndSave(): Promise<void> {
    const spent: number = this.totalMinutes * 60 - this.remainSec;
    const minutes: number = Math.floor(spent / 60);
    this.clearTimer();
    this.running = false;
    if (minutes >= 5 && !this.onBreak) {
      await this.report(minutes);
      this.completed = this.completed + 1;
      toast(`已记录 ${minutes} 分钟`);
    } else {
      toast('不足 5 分钟，未记入统计');
    }
    this.remainSec = this.totalMinutes * 60;
    this.onBreak = false;
  }

  private timeText(): string {
    const m: number = Math.floor(this.remainSec / 60);
    const s: number = this.remainSec % 60;
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  }

  private percent(): number {
    const total: number = (this.onBreak ? this.breakMinutes : this.totalMinutes) * 60;
    if (total === 0) {
      return 0;
    }
    return ((total - this.remainSec) / total) * 100;
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: '专注',
        subtitle: this.onBreak ? '休息中' : '专注中',
        onBack: () => {
          router.back();
        },
      });
      Scroll() {
        Column({ space: Theme.GAP }) {
          Card({
            content: () => {
              this.timerSection();
            },
          });
          Card({
            content: () => {
              this.durationSection();
            },
          });
          Card({
            content: () => {
              this.taskSection();
            },
          });
          Row().height(16);
        }
        .width('100%')
        .padding({ left: Theme.PAGE_PADDING, right: Theme.PAGE_PADDING, top: 12 });
      }
      .layoutWeight(1)
      .scrollBar(BarState.Off);
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  timerSection() {
    Column({ space: 14 }) {
      Stack() {
        Progress({
          value: this.percent(),
          total: 100,
          type: ProgressType.Ring,
        })
          .width(200)
          .height(200)
          .color(this.onBreak ? Theme.OK : Theme.BRAND)
          .style({ strokeWidth: 12 });
        Column({ space: 5 }) {
          Text(this.timeText())
            .fontSize(44)
            .fontWeight(FontWeight.Bold)
            .fontColor(Theme.TEXT);
          Text(this.onBreak ? '休息' : '专注')
            .fontSize(13)
            .fontColor(Theme.TEXT_SUB);
        }
      }
      .width('100%')
      .height(210);

      Row({ space: 12 }) {
        Button(this.running ? '暂停' : '开始')
          .layoutWeight(1)
          .height(46)
          .borderRadius(12)
          .backgroundColor(this.running ? '#F1F3F5' : Theme.BRAND)
          .fontColor(this.running ? Theme.TEXT : '#FFFFFF')
          .onClick(() => {
            if (this.running) {
              this.pause();
            } else {
              this.start();
            }
          });
        Button('结束')
          .layoutWeight(1)
          .height(46)
          .borderRadius(12)
          .backgroundColor('#F1F3F5')
          .fontColor(Theme.TEXT)
          .onClick(() => {
            this.stopAndSave();
          });
        Button('重置')
          .width(70)
          .height(46)
          .borderRadius(12)
          .backgroundColor('#F1F3F5')
          .fontColor(Theme.TEXT_SUB)
          .onClick(() => {
            this.reset();
          });
      }
      .width('100%');

      Text(`本次进入已完成 ${this.completed} 段`)
        .fontSize(11)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%')
    .alignItems(HorizontalAlign.Center);
  }

  @Builder
  durationSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '时长' });
      Row({ space: 8 }) {
        ForEach([15, 25, 30, 45, 60], (m: number) => {
          Text(`${m}分`)
            .fontSize(13)
            .fontColor(this.totalMinutes === m ? '#FFFFFF' : Theme.TEXT_SUB)
            .backgroundColor(this.totalMinutes === m ? Theme.BRAND : '#F1F3F5')
            .borderRadius(9)
            .padding({ left: 12, right: 12, top: 7, bottom: 7 })
            .onClick(() => {
              if (this.running) {
                toast('请先暂停再调整时长');
                return;
              }
              this.totalMinutes = m;
              this.remainSec = m * 60;
            });
        }, (m: number) => `${m}`);
      }
      .width('100%');
      Text(`休息 ${this.breakMinutes} 分钟（可在偏好设置中修改默认值）`)
        .fontSize(11)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%');
  }

  @Builder
  taskSection() {
    Column({ space: 8 }) {
      SectionTitle({ title: '关联任务（可选）' });
      Text('关联后这段专注会计入该任务，便于回看时间花在了哪')
        .fontSize(11)
        .fontColor(Theme.TEXT_WEAK);
      Flex({ wrap: FlexWrap.Wrap }) {
        Text('不关联')
          .fontSize(12)
          .fontColor(this.boundTaskId === 0 ? '#FFFFFF' : Theme.TEXT_SUB)
          .backgroundColor(this.boundTaskId === 0 ? Theme.TEXT_SUB : '#F1F3F5')
          .borderRadius(8)
          .padding({ left: 10, right: 10, top: 5, bottom: 5 })
          .margin({ right: 7, bottom: 7 })
          .onClick(() => {
            this.boundTaskId = 0;
          });
        ForEach(this.tasks, (t: TaskOut) => {
          Text(t.title)
            .fontSize(12)
            .fontColor(this.boundTaskId === t.id ? '#FFFFFF' : Theme.TEXT_SUB)
            .backgroundColor(this.boundTaskId === t.id ? Theme.BRAND : '#F1F3F5')
            .borderRadius(8)
            .padding({ left: 10, right: 10, top: 5, bottom: 5 })
            .margin({ right: 7, bottom: 7 })
            .constraintSize({ maxWidth: 180 })
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
            .onClick(() => {
              this.boundTaskId = this.boundTaskId === t.id ? 0 : t.id;
            });
        }, (t: TaskOut) => `${t.id}`);
      }
      .width('100%');
    }
    .width('100%');
  }
}
