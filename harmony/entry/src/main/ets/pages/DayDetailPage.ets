/**
 * 单日详情：黄历 + 当日任务 + 当日记录。
 *
 * 数据来源分两层：
 * 1) 离线农历（`Lunar.ets`）先渲染，页面**立即**可读；
 * 2) 后端 `/api/lunar/{date}` 返回宜忌/神位/物候后再合并覆盖。
 * 这样即使接口慢或不可用，用户也不会看到一片空白。
 */
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import {
  computeLunar,
  daysWeekText,
  ganzhiYearText,
  godPositions,
  GodPosition,
  jiList,
  lunarYmd,
  mergeLunar,
  termText,
  wuhouShort,
  yiList,
} from '../common/Lunar';
import { HolidayInfo, LunarInfo, RecordOut, TaskOut } from '../common/Models';
import { Theme } from '../common/Theme';
import { toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { Card, EmptyTip, NavBar, SectionTitle } from '../view/Common';
import { TaskItem, TaskItemModel, wrapTasks } from '../view/TaskItem';

interface DayDetailParams {
  date?: string;
}

@Entry
@Component
struct DayDetailPage {
  @State private date: string = '';
  @State private lunar: LunarInfo | null = null;
  @State private holiday: string = '';
  @State private isOffDay: boolean = false;
  @State private tasks: TaskItemModel[] = [];
  @State private records: RecordOut[] = [];
  @State private loadingRemote: boolean = true;

  aboutToAppear(): void {
    const params = router.getParams() as DayDetailParams;
    this.date = params?.date ?? DateUtil.today();
    // 先出离线结果，保证首帧有内容
    this.lunar = computeLunar(this.date);
    this.loadRemote();
    this.loadDayData();
  }

  onPageShow(): void {
    this.loadDayData();
  }

  private async loadRemote(): Promise<void> {
    try {
      const remote: LunarInfo = await Api.lunar(this.date);
      this.lunar = mergeLunar(computeLunar(this.date), remote);
    } catch (e) {
      // 保持离线结果即可，不打扰用户
    }
    try {
      const map: Record<string, HolidayInfo> = await Api.holidays(DateUtil.yearOf(this.date));
      const h: HolidayInfo | undefined = map[this.date];
      this.holiday = h?.name ?? '';
      this.isOffDay = h?.isOffDay ?? false;
    } catch (e) {
    }
    this.loadingRemote = false;
  }

  private async loadDayData(): Promise<void> {
    try {
      const tasks: TaskOut[] = await Api.tasks({
        due_from: this.date,
        due_to: this.date,
        status: 'all',
        limit: 200,
      });
      this.tasks = wrapTasks(tasks);
    } catch (e) {
    }
    try {
      this.records = await Api.records({ date: this.date, limit: 100 });
    } catch (e) {
    }
  }

  private async toggle(task: TaskOut): Promise<void> {
    try {
      await Api.updateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' });
      await this.loadDayData();
      AppStore.syncReminders().catch(() => {
      });
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: `${DateUtil.monthOf(this.date)}月${DateUtil.dayOf(this.date)}日`,
        subtitle: DateUtil.weekdayLabel(this.date),
        onBack: () => {
          router.back();
        },
      });
      Scroll() {
        Column({ space: Theme.GAP }) {
          Card({
            content: () => {
              this.almanacHeader();
            },
          });
          if (yiList(this.lunar).length > 0 || jiList(this.lunar).length > 0) {
            Card({
              content: () => {
                this.yiJiSection();
              },
            });
          }
          if (godPositions(this.lunar).length > 0 || wuhouShort(this.lunar).length > 0) {
            Card({
              content: () => {
                this.extraSection();
              },
            });
          }
          Card({
            content: () => {
              this.taskSection();
            },
          });
          Card({
            content: () => {
              this.recordSection();
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
  almanacHeader() {
    Column({ space: 7 }) {
      Row({ space: 8 }) {
        Text(`${DateUtil.dayOf(this.date)}`)
          .fontSize(38)
          .fontWeight(FontWeight.Bold)
          .fontColor(this.isOffDay ? Theme.DANGER : Theme.TEXT);
        Column({ space: 3 }) {
          Text(lunarYmd(this.lunar)).fontSize(14).fontColor(Theme.TEXT);
          Text(ganzhiYearText(this.lunar)).fontSize(12).fontColor(Theme.TEXT_SUB);
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1);
        if (this.holiday.length > 0) {
          Text(this.holiday)
            .fontSize(12)
            .fontColor(this.isOffDay ? Theme.DANGER : Theme.OK)
            .backgroundColor(this.isOffDay ? '#FEF2F2' : '#ECFDF5')
            .borderRadius(8)
            .padding({ left: 8, right: 8, top: 3, bottom: 3 });
        }
      }
      .width('100%')
      .alignItems(VerticalAlign.Center);

      Flex({ wrap: FlexWrap.Wrap }) {
        if (termText(this.lunar).length > 0) {
          this.metaChip('节气', termText(this.lunar), Theme.OK);
        }
        if (this.lunar?.jieri && this.lunar.jieri.length > 0) {
          this.metaChip('节日', this.lunar.jieri, Theme.DANGER);
        }
        if (this.lunar?.xingzuo && this.lunar.xingzuo.length > 0) {
          this.metaChip('星座', `${this.lunar.xingzuo}座`, Theme.PURPLE);
        }
        if (this.lunar?.YUEXIANG && this.lunar.YUEXIANG.length > 0) {
          this.metaChip('月相', this.lunar.YUEXIANG, Theme.BRAND);
        }
      }
      .width('100%');

      Text(daysWeekText(this.lunar, this.date)).fontSize(11).fontColor(Theme.TEXT_WEAK);
    }
    .width('100%');
  }

  @Builder
  metaChip(label: string, value: string, color: string) {
    Row({ space: 3 }) {
      Text(label).fontSize(10).fontColor(Theme.TEXT_WEAK);
      Text(value).fontSize(12).fontColor(color);
    }
    .margin({ right: 12, top: 2 });
  }

  @Builder
  yiJiSection() {
    Column({ space: 8 }) {
      SectionTitle({ title: '宜忌' });
      Row({ space: 8 }) {
        Text('宜')
          .fontSize(13)
          .fontColor('#FFFFFF')
          .width(22)
          .height(22)
          .textAlign(TextAlign.Center)
          .backgroundColor(Theme.OK)
          .borderRadius(11);
        Text(yiList(this.lunar).join('、'))
          .fontSize(13)
          .fontColor(Theme.TEXT)
          .layoutWeight(1);
      }
      .width('100%')
      .alignItems(VerticalAlign.Top);
      Row({ space: 8 }) {
        Text('忌')
          .fontSize(13)
          .fontColor('#FFFFFF')
          .width(22)
          .height(22)
          .textAlign(TextAlign.Center)
          .backgroundColor(Theme.DANGER)
          .borderRadius(11);
        Text(jiList(this.lunar).join('、'))
          .fontSize(13)
          .fontColor(Theme.TEXT)
          .layoutWeight(1);
      }
      .width('100%')
      .alignItems(VerticalAlign.Top);
      Text('黄历内容仅供参考，安排以你的实际计划为准')
        .fontSize(10)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%');
  }

  @Builder
  extraSection() {
    Column({ space: 8 }) {
      SectionTitle({ title: '更多' });
      if (wuhouShort(this.lunar).length > 0) {
        Row({ space: 6 }) {
          Text('物候').fontSize(11).fontColor(Theme.TEXT_WEAK);
          Text(wuhouShort(this.lunar)).fontSize(13).fontColor(Theme.TEXT);
        }
        .width('100%');
      }
      if (godPositions(this.lunar).length > 0) {
        Flex({ wrap: FlexWrap.Wrap }) {
          ForEach(godPositions(this.lunar), (p: GodPosition) => {
            Row({ space: 3 }) {
              Text(p.label).fontSize(10).fontColor(Theme.TEXT_WEAK);
              Text(p.value).fontSize(12).fontColor(Theme.TEXT);
            }
            .margin({ right: 12, top: 3 });
          }, (p: GodPosition) => p.label);
        }
        .width('100%');
      }
    }
    .width('100%');
  }

  @Builder
  taskSection() {
    Column({ space: 4 }) {
      SectionTitle({
        title: `当日任务（${this.tasks.length}）`,
        action: '＋ 新建',
        onAction: () => {
          router.pushUrl({
            url: 'pages/TaskEditPage',
            params: { presetDate: this.date },
          });
        },
      });
      if (this.tasks.length === 0) {
        EmptyTip({ text: '这天没有安排任务' });
      } else {
        ForEach(this.tasks, (m: TaskItemModel) => {
          Column() {
            TaskItem({
              task: m,
              onToggle: (t: TaskOut) => {
                this.toggle(t);
              },
              onTap: (t: TaskOut) => {
                router.pushUrl({ url: 'pages/TaskEditPage', params: { taskId: t.id } });
              },
            });
            Divider().color(Theme.BORDER).strokeWidth(0.5);
          }
          .width('100%');
        }, (m: TaskItemModel) => `${m.data.id}-${m.data.status}`);
      }
    }
    .width('100%');
  }

  @Builder
  recordSection() {
    Column({ space: 8 }) {
      SectionTitle({
        title: `当日记录（${this.records.length}）`,
        action: '＋ 记一笔',
        onAction: () => {
          router.pushUrl({
            url: 'pages/RecordEditPage',
            params: { presetDate: this.date },
          });
        },
      });
      if (this.records.length === 0) {
        EmptyTip({ text: '这天还没有记录' });
      } else {
        ForEach(this.records, (r: RecordOut) => {
          Column({ space: 3 }) {
            Row({ space: 6 }) {
              Text(Theme.recordTypeLabel(r.type)).fontSize(10).fontColor(Theme.BRAND);
              Text(r.title)
                .fontSize(14)
                .fontColor(Theme.TEXT)
                .layoutWeight(1)
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis });
              if (r.mood && r.mood.length > 0) {
                Text(r.mood).fontSize(13);
              }
            }
            .width('100%');
            if (r.content && r.content.length > 0) {
              Text(r.content)
                .fontSize(12)
                .fontColor(Theme.TEXT_SUB)
                .maxLines(2)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
                .width('100%');
            }
          }
          .width('100%')
          .padding({ top: 6, bottom: 6 })
          .onClick(() => {
            router.pushUrl({ url: 'pages/RecordEditPage', params: { recordId: r.id } });
          });
        }, (r: RecordOut) => `${r.id}-${r.updated_at ?? ''}`);
      }
    }
    .width('100%');
  }
}
