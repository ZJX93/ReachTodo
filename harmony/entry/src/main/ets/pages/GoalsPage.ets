/**
 * 目标看板：进度、逾期、截止一目了然。
 *
 * 用 `/api/goals/board` 而不是 `/api/goals` + 逐个查任务：
 * 后者是典型 N+1，10 个目标要发 11 次请求。
 */
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import { GoalBoardItem } from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText } from '../common/Toast';
import { EmptyTip, NavBar, ProgressBar, SegmentPicker, StateHint } from '../view/Common';

@Entry
@Component
struct GoalsPage {
  @State private loading: boolean = true;
  @State private error: string = '';
  @State private goals: GoalBoardItem[] = [];
  @State private filter: string = 'active';

  aboutToAppear(): void {
    this.load();
  }

  onPageShow(): void {
    if (!this.loading) {
      this.load();
    }
  }

  private async load(): Promise<void> {
    this.loading = this.goals.length === 0;
    this.error = '';
    try {
      this.goals = await Api.goalsBoard();
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  private visible(): GoalBoardItem[] {
    if (this.filter === 'all') {
      return this.goals;
    }
    return this.goals.filter((g: GoalBoardItem) => g.status === this.filter);
  }

  build() {
    Stack({ alignContent: Alignment.BottomEnd }) {
      Column({ space: 0 }) {
        NavBar({
          title: '目标',
          subtitle: '把长期方向拆成可执行的任务',
          onBack: () => {
            router.back();
          },
        });
        Row() {
          SegmentPicker({
            labels: ['进行中', '已完成', '全部'],
            values: ['active', 'done', 'all'],
            selected: this.filter,
            onSelect: (v: string) => {
              this.filter = v;
            },
          });
        }
        .width('100%')
        .padding({ left: 14, right: 14, top: 10, bottom: 10 })
        .backgroundColor(Theme.CARD);

        if (this.loading || this.error.length > 0) {
          StateHint({
            loading: this.loading,
            error: this.error,
            onRetry: () => {
              this.load();
            },
          });
        } else if (this.visible().length === 0) {
          EmptyTip({
            text: '还没有目标',
            hint: '例如「今年读完 12 本书」，再把它拆成每月一本的任务',
          });
        } else {
          List({ space: 10 }) {
            ForEach(this.visible(), (g: GoalBoardItem) => {
              ListItem() {
                this.goalCard(g);
              }
            }, (g: GoalBoardItem) => `${g.id}-${g.progress}-${g.status}`);
          }
          .width('100%')
          .layoutWeight(1)
          .padding({ left: 14, right: 14, top: 10, bottom: 10 })
          .scrollBar(BarState.Off);
        }
      }
      .width('100%')
      .height('100%');

      Button('＋')
        .width(54)
        .height(54)
        .borderRadius(27)
        .fontSize(26)
        .backgroundColor(Theme.PURPLE)
        .margin({ right: 18, bottom: 20 })
        .onClick(() => {
          router.pushUrl({ url: 'pages/GoalEditPage' });
        });
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  goalCard(g: GoalBoardItem) {
    Column({ space: 8 }) {
      Row({ space: 8 }) {
        Text(g.title)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor(Theme.TEXT)
          .layoutWeight(1)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis });
        if (g.status === 'done') {
          Text('已完成')
            .fontSize(11)
            .fontColor(Theme.OK)
            .backgroundColor('#ECFDF5')
            .borderRadius(6)
            .padding({ left: 6, right: 6, top: 2, bottom: 2 });
        }
      }
      .width('100%');

      if (g.description && g.description.length > 0) {
        Text(g.description)
          .fontSize(12)
          .fontColor(Theme.TEXT_SUB)
          .maxLines(2)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%');
      }

      ProgressBar({ percent: g.progress, color: Theme.PURPLE });

      Row({ space: 10 }) {
        Text(`${g.done}/${g.total} 项 · ${g.progress}%`).fontSize(11).fontColor(Theme.TEXT_SUB);
        if (g.overdue > 0) {
          Text(`逾期 ${g.overdue}`).fontSize(11).fontColor(Theme.DANGER);
        }
        Blank();
        if (g.deadline) {
          Text(this.deadlineText(g.deadline))
            .fontSize(11)
            .fontColor(DateUtil.isOverdue(g.deadline) && g.status !== 'done'
              ? Theme.DANGER : Theme.TEXT_WEAK);
        }
      }
      .width('100%');
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
    .padding(14)
    .backgroundColor(Theme.CARD)
    .borderRadius(Theme.RADIUS)
    .onClick(() => {
      router.pushUrl({ url: 'pages/GoalEditPage', params: { goalId: g.id } });
    });
  }

  private deadlineText(deadline: string): string {
    const diff: number = DateUtil.diffDays(deadline, DateUtil.today());
    if (diff < 0) {
      return `已超期 ${-diff} 天`;
    }
    if (diff === 0) {
      return '今天截止';
    }
    return `剩 ${diff} 天`;
  }
}
