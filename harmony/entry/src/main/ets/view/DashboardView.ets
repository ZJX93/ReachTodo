/**
 * 看板：进入应用的第一屏。
 *
 * 信息优先级（自上而下）：今天是什么日子 → 我今天要做什么 → 我的长期目标进展。
 * 「长期目标」放在首屏是本项目与通用待办的核心差异，不能折叠到二级页。
 */
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import { computeLunar, lunarLabel } from '../common/Lunar';
import {
  GoalBoardItem,
  LunarInfo,
  TaskOut,
  TaskSummary,
  TaskSummaryCategory,
} from '../common/Models';
import { Prefs } from '../common/Prefs';
import { Theme } from '../common/Theme';
import { errorText, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { Card, EmptyTip, ProgressBar, SectionTitle, StateHint } from './Common';
import { TaskItem, TaskItemModel, wrapTasks } from './TaskItem';

@Component
export struct DashboardView {
  @State private loading: boolean = true;
  @State private error: string = '';
  @State private summary: TaskSummary | null = null;
  @State private todayTasks: TaskItemModel[] = [];
  @State private goals: GoalBoardItem[] = [];
  @State private lunarText: string = '';
  /** 父页在「切回本 Tab / 从编辑页返回」时自增，用 @Watch 触发重新拉取。 */
  @Link @Watch('onRefreshKeyChange') refreshKey: number;

  aboutToAppear(): void {
    this.lunarText = lunarLabel(computeLunar(DateUtil.today()));
    this.load();
  }

  onRefreshKeyChange(): void {
    this.load();
  }

  private async load(): Promise<void> {
    this.loading = this.summary === null;
    this.error = '';
    try {
      // 三个请求互相独立，并发发出。Promise.all 任一失败即整体失败，
      // 这里可以接受：首屏三块数据缺一块都不完整，不如统一给重试。
      const today: string = DateUtil.today();
      const results = await Promise.all([
        Api.taskSummary(),
        Api.tasks({ status: 'todo', due_to: today, sort: 'priority', limit: 60 }),
        Api.goalsBoard(),
      ]);
      this.summary = results[0] as TaskSummary;
      this.todayTasks = wrapTasks(results[1] as TaskOut[]);
      this.goals = (results[2] as GoalBoardItem[])
        .filter((g: GoalBoardItem) => g.status === 'active');
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  private async toggle(task: TaskOut): Promise<void> {
    const next: string = task.status === 'done' ? 'todo' : 'done';
    try {
      await Api.updateTask(task.id, { status: next });
      await this.load();
      AppStore.syncReminders().catch(() => {
      });
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Scroll() {
      Column({ space: Theme.GAP }) {
        // ---------------- 日期 + 农历 ----------------
        Card({
          content: () => {
            this.headerContent();
          },
        });

        // ---------------- 数量总览 ----------------
        if (this.summary) {
          Row({ space: Theme.GAP }) {
            this.statBox('今日待办', this.summary!.today_todo, Theme.BRAND);
            this.statBox('已逾期', this.summary!.overdue, Theme.DANGER);
            this.statBox('累计完成', this.summary!.total_done, Theme.OK);
          }
          .width('100%');
        }

        // ---------------- 快捷入口 ----------------
        Card({
          content: () => {
            this.quickEntries();
          },
        });

        // ---------------- 今日待办 ----------------
        Card({
          content: () => {
            this.todaySection();
          },
        });

        // ---------------- 维度分布 ----------------
        if (this.summary && this.summary!.categories.length > 0) {
          Card({
            content: () => {
              this.categorySection();
            },
          });
        }

        // ---------------- 目标进展 ----------------
        Card({
          content: () => {
            this.goalSection();
          },
        });

        Row().height(8);
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
  headerContent() {
    Column({ space: 6 }) {
      Row({ space: 8 }) {
        Text(`${DateUtil.monthOf(DateUtil.today())}月${DateUtil.dayOf(DateUtil.today())}日`)
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.TEXT);
        Text(DateUtil.weekdayLabel(DateUtil.today()))
          .fontSize(14)
          .fontColor(Theme.TEXT_SUB);
      }
      .width('100%')
      .alignItems(VerticalAlign.Bottom);

      Text(this.lunarText.length > 0 ? this.lunarText : '—')
        .fontSize(13)
        .fontColor(Theme.TEXT_SUB);
      Text(this.greeting())
        .fontSize(13)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start);
  }

  private greeting(): string {
    const name: string = Prefs.username();
    return name.length > 0 ? `${name}，今天也要抵达一点点` : '今天也要抵达一点点';
  }

  @Builder
  statBox(label: string, value: number, color: string) {
    Column({ space: 4 }) {
      Text(`${value}`).fontSize(22).fontWeight(FontWeight.Bold).fontColor(color);
      Text(label).fontSize(12).fontColor(Theme.TEXT_SUB);
    }
    .layoutWeight(1)
    .padding({ top: 12, bottom: 12 })
    .backgroundColor(Theme.CARD)
    .borderRadius(Theme.RADIUS);
  }

  @Builder
  quickEntries() {
    Row() {
      this.entryCell('四象限', '#EEF2FF', Theme.BRAND_DARK, 'pages/MatrixPage');
      this.entryCell('周回顾', '#ECFDF5', '#047857', 'pages/StatsPage');
      this.entryCell('专注', '#FEF3C7', '#B45309', 'pages/FocusPage');
      this.entryCell('目标', '#F5F3FF', '#6D28D9', 'pages/GoalsPage');
    }
    .width('100%');
  }

  @Builder
  entryCell(label: string, bg: string, fg: string, url: string) {
    Column({ space: 6 }) {
      Text(label.substring(0, 1))
        .fontSize(17)
        .fontWeight(FontWeight.Bold)
        .fontColor(fg)
        .width(38)
        .height(38)
        .textAlign(TextAlign.Center)
        .backgroundColor(bg)
        .borderRadius(12);
      Text(label).fontSize(12).fontColor(Theme.TEXT_SUB);
    }
    .layoutWeight(1)
    .onClick(() => {
      router.pushUrl({ url: url });
    });
  }

  @Builder
  todaySection() {
    Column() {
      SectionTitle({
        title: '今天与逾期',
        action: '四象限',
        onAction: () => {
          router.pushUrl({ url: 'pages/MatrixPage' });
        },
      });
      if (this.loading || this.error.length > 0) {
        StateHint({
          loading: this.loading,
          error: this.error,
          onRetry: () => {
            this.load();
          },
        });
      } else if (this.todayTasks.length === 0) {
        EmptyTip({ text: '今天没有待办', hint: '在「任务」页新建，或先去「目标」拆解一个长期目标' });
      } else {
        ForEach(this.todayTasks, (m: TaskItemModel) => {
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
        }, (m: TaskItemModel) => `${m.data.id}-${m.data.status}`);
      }
    }
    .width('100%');
  }

  @Builder
  categorySection() {
    Column({ space: 8 }) {
      SectionTitle({ title: '维度分布' });
      ForEach(this.summary!.categories, (c: TaskSummaryCategory) => {
        Column({ space: 5 }) {
          Row() {
            Text(`${c.icon} ${c.name}`).fontSize(13).fontColor(Theme.TEXT).layoutWeight(1);
            Text(`${c.done}/${c.done + c.todo}`).fontSize(12).fontColor(Theme.TEXT_SUB);
          }
          .width('100%');
          ProgressBar({
            percent: c.done + c.todo > 0 ? (c.done / (c.done + c.todo)) * 100 : 0,
            color: c.color,
          });
        }
        .width('100%');
      }, (c: TaskSummaryCategory) => `${c.category_id}`);
    }
    .width('100%');
  }

  @Builder
  goalSection() {
    Column({ space: 10 }) {
      SectionTitle({
        title: '目标进展',
        action: '管理',
        onAction: () => {
          router.pushUrl({ url: 'pages/GoalsPage' });
        },
      });
      if (this.goals.length === 0) {
        EmptyTip({ text: '还没有进行中的目标', hint: '目标是把「想做」变成「在做」的抓手' });
      } else {
        ForEach(this.goals, (g: GoalBoardItem) => {
          Column({ space: 6 }) {
            Row() {
              Text(g.title)
                .fontSize(14)
                .fontColor(Theme.TEXT)
                .layoutWeight(1)
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis });
              Text(`${g.progress}%`).fontSize(12).fontColor(Theme.PURPLE);
            }
            .width('100%');
            ProgressBar({ percent: g.progress, color: Theme.PURPLE });
            Row({ space: 10 }) {
              Text(`共 ${g.total} 项 · 完成 ${g.done}`).fontSize(11).fontColor(Theme.TEXT_SUB);
              if (g.overdue > 0) {
                Text(`逾期 ${g.overdue}`).fontSize(11).fontColor(Theme.DANGER);
              }
              if (g.deadline) {
                Text(`截止 ${g.deadline}`).fontSize(11).fontColor(Theme.TEXT_WEAK);
              }
            }
            .width('100%');
          }
          .width('100%')
          .onClick(() => {
            router.pushUrl({ url: 'pages/GoalEditPage', params: { goalId: g.id } });
          });
        }, (g: GoalBoardItem) => `${g.id}-${g.progress}`);
      }
    }
    .width('100%');
  }
}
