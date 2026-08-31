/**
 * 周回顾 / 统计。
 *
 * 「回顾」比「统计」重要：数字只是入口，真正有价值的是让用户看到
 * 本周完成了什么、哪些逾期了、目标推进了多少，从而决定下周怎么调整。
 * 因此本页在概览之后必须给出**具体条目**，而不是只有图表。
 */
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import { CategoryStat, GoalProgress, StatsSummary, TaskOut } from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import {
  Card,
  EmptyTip,
  NavBar,
  ProgressBar,
  SectionTitle,
  StateHint,
} from '../view/Common';

@Entry
@Component
struct StatsPage {
  @State private loading: boolean = true;
  @State private error: string = '';
  @State private stats: StatsSummary | null = null;
  @State private weekDone: TaskOut[] = [];
  @State private overdue: TaskOut[] = [];
  @State private weekStart: string = '';
  @State private weekEnd: string = '';

  aboutToAppear(): void {
    this.load();
  }

  private async load(): Promise<void> {
    this.loading = this.stats === null;
    this.error = '';
    const today: string = DateUtil.today();
    this.weekStart = DateUtil.weekStartOf(today, AppStore.settings().weekStart);
    this.weekEnd = DateUtil.addDays(this.weekStart, 6);
    try {
      this.stats = await Api.statsSummary();
      // 本周「已完成」按到期日落在本周区间取，与后端 week_completed 的口径
      // （按完成时间）略有差异，这里展示的是「本周该做且做完的事」
      this.weekDone = await Api.tasks({
        status: 'done',
        due_from: this.weekStart,
        due_to: this.weekEnd,
        limit: 200,
      });
      this.overdue = await Api.tasks({ status: 'todo', overdue: true, sort: 'due', limit: 100 });
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: '周回顾',
        subtitle: `${this.weekStart} ~ ${this.weekEnd}`,
        onBack: () => {
          router.back();
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
      } else {
        Scroll() {
          Column({ space: Theme.GAP }) {
            Card({
              content: () => {
                this.overviewSection();
              },
            });
            Card({
              content: () => {
                this.focusSection();
              },
            });
            if (this.stats!.per_category.length > 0) {
              Card({
                content: () => {
                  this.categorySection();
                },
              });
            }
            if (this.stats!.goals_progress.length > 0) {
              Card({
                content: () => {
                  this.goalSection();
                },
              });
            }
            Card({
              content: () => {
                this.weekDoneSection();
              },
            });
            Card({
              content: () => {
                this.overdueSection();
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
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  overviewSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '概览' });
      Row() {
        this.cell('待办', `${this.stats!.total_todo}`, Theme.BRAND);
        this.cell('累计完成', `${this.stats!.total_done}`, Theme.OK);
        this.cell('本周完成', `${this.stats!.week_completed}`, Theme.PURPLE);
        this.cell('连续打卡', `${this.stats!.streak}天`, Theme.WARN);
      }
      .width('100%');
      Text(this.streakHint()).fontSize(11).fontColor(Theme.TEXT_SUB);
    }
    .width('100%');
  }

  private streakHint(): string {
    const s: number = this.stats!.streak;
    if (s === 0) {
      return '今天还没有完成任何任务，完成一件即可开始连续记录';
    }
    if (s < 3) {
      return '连续记录刚开始，保持住';
    }
    if (s < 7) {
      return '已经形成节奏，再坚持几天就满一周';
    }
    return '很稳定的节奏，注意别把强度定得太满';
  }

  @Builder
  cell(label: string, value: string, color: string) {
    Column({ space: 3 }) {
      Text(value).fontSize(18).fontWeight(FontWeight.Bold).fontColor(color);
      Text(label).fontSize(11).fontColor(Theme.TEXT_SUB);
    }
    .layoutWeight(1);
  }

  @Builder
  focusSection() {
    Column({ space: 8 }) {
      SectionTitle({
        title: '专注',
        action: '去专注',
        onAction: () => {
          router.pushUrl({ url: 'pages/FocusPage' });
        },
      });
      Row() {
        this.cell('今日', `${this.stats!.focus_minutes_today}分`, Theme.BRAND);
        this.cell('本周', `${this.stats!.focus_minutes_week}分`, Theme.BRAND_DARK);
        this.cell('周均/天', `${Math.round(this.stats!.focus_minutes_week / 7)}分`, Theme.TEXT_SUB);
      }
      .width('100%');
    }
    .width('100%');
  }

  @Builder
  categorySection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '维度投入' });
      ForEach(this.stats!.per_category, (c: CategoryStat) => {
        Column({ space: 5 }) {
          Row() {
            Text(`${c.icon} ${c.name}`).fontSize(13).fontColor(Theme.TEXT).layoutWeight(1);
            Text(`完成 ${c.done} · 待办 ${c.todo}`).fontSize(11).fontColor(Theme.TEXT_SUB);
          }
          .width('100%');
          ProgressBar({
            percent: c.done + c.todo > 0 ? (c.done / (c.done + c.todo)) * 100 : 0,
            color: c.color,
          });
        }
        .width('100%');
      }, (c: CategoryStat) => c.name);
      Text('某个维度长期为 0，说明它在你的生活里被挤掉了——这正是分维度的意义')
        .fontSize(11)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%');
  }

  @Builder
  goalSection() {
    Column({ space: 10 }) {
      SectionTitle({
        title: '目标推进',
        action: '管理',
        onAction: () => {
          router.pushUrl({ url: 'pages/GoalsPage' });
        },
      });
      ForEach(this.stats!.goals_progress, (g: GoalProgress) => {
        Column({ space: 5 }) {
          Row() {
            Text(g.title)
              .fontSize(13)
              .fontColor(Theme.TEXT)
              .layoutWeight(1)
              .maxLines(1)
              .textOverflow({ overflow: TextOverflow.Ellipsis });
            Text(`${g.done}/${g.total} · ${g.progress}%`)
              .fontSize(11)
              .fontColor(Theme.PURPLE);
          }
          .width('100%');
          ProgressBar({ percent: g.progress, color: Theme.PURPLE });
        }
        .width('100%')
        .onClick(() => {
          router.pushUrl({ url: 'pages/GoalEditPage', params: { goalId: g.id } });
        });
      }, (g: GoalProgress) => `${g.id}-${g.progress}`);
    }
    .width('100%');
  }

  @Builder
  weekDoneSection() {
    Column({ space: 6 }) {
      SectionTitle({ title: `本周完成（${this.weekDone.length}）` });
      if (this.weekDone.length === 0) {
        EmptyTip({ text: '本周还没有完成的任务' });
      } else {
        ForEach(this.weekDone, (t: TaskOut) => {
          Row({ space: 8 }) {
            Text('✓').fontSize(13).fontColor(Theme.OK);
            Text(t.title)
              .fontSize(13)
              .fontColor(Theme.TEXT_SUB)
              .layoutWeight(1)
              .maxLines(1)
              .textOverflow({ overflow: TextOverflow.Ellipsis });
            Text(DateUtil.humanDue(t.due_date)).fontSize(11).fontColor(Theme.TEXT_WEAK);
          }
          .width('100%')
          .padding({ top: 5, bottom: 5 })
          .onClick(() => {
            router.pushUrl({ url: 'pages/TaskEditPage', params: { taskId: t.id } });
          });
        }, (t: TaskOut) => `${t.id}`);
      }
    }
    .width('100%');
  }

  @Builder
  overdueSection() {
    Column({ space: 6 }) {
      SectionTitle({ title: `待处理逾期（${this.overdue.length}）` });
      if (this.overdue.length === 0) {
        EmptyTip({ text: '没有逾期任务', hint: '保持这个状态' });
      } else {
        Text('逾期不代表失败，但需要决定：重新排期、拆小，还是干脆删掉')
          .fontSize(11)
          .fontColor(Theme.TEXT_SUB);
        ForEach(this.overdue, (t: TaskOut) => {
          Row({ space: 8 }) {
            Text('!').fontSize(13).fontColor(Theme.DANGER);
            Text(t.title)
              .fontSize(13)
              .fontColor(Theme.TEXT)
              .layoutWeight(1)
              .maxLines(1)
              .textOverflow({ overflow: TextOverflow.Ellipsis });
            Text(DateUtil.humanDue(t.due_date)).fontSize(11).fontColor(Theme.DANGER);
          }
          .width('100%')
          .padding({ top: 5, bottom: 5 })
          .onClick(() => {
            router.pushUrl({ url: 'pages/TaskEditPage', params: { taskId: t.id } });
          });
        }, (t: TaskOut) => `${t.id}`);
      }
    }
    .width('100%');
  }
}
