/**
 * 四象限（重要 × 紧急）。
 *
 * 象限划分由**后端**给出（`GET /api/tasks/matrix`），客户端不重复实现判定逻辑：
 * 三端各写一遍必然漂移，而「同一条任务在手机和网页上落在不同象限」
 * 会直接摧毁这个视图的可信度。
 */
import router from '@ohos.router';
import { Api } from '../common/Api';
import { MatrixQuadrant, TaskOut } from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { NavBar, StateHint } from '../view/Common';
import { TaskItem, TaskItemModel, wrapTasks } from '../view/TaskItem';

interface QuadrantVM {
  key: string;
  title: string;
  sub: string;
  color: string;
  bg: string;
  tasks: TaskItemModel[];
}

@Entry
@Component
struct MatrixPage {
  @State private loading: boolean = true;
  @State private error: string = '';
  @State private quadrants: QuadrantVM[] = [];
  @State private expanded: string = '';

  aboutToAppear(): void {
    this.load();
  }

  onPageShow(): void {
    if (!this.loading) {
      this.load();
    }
  }

  private colorOf(key: string): string {
    if (key === 'q1') {
      return Theme.DANGER;
    }
    if (key === 'q2') {
      return Theme.BRAND;
    }
    if (key === 'q3') {
      return Theme.WARN;
    }
    return Theme.TEXT_SUB;
  }

  private bgOf(key: string): string {
    if (key === 'q1') {
      return '#FEF2F2';
    }
    if (key === 'q2') {
      return '#EFF6FF';
    }
    if (key === 'q3') {
      return '#FFFBEB';
    }
    return '#F8FAFC';
  }

  private async load(): Promise<void> {
    this.loading = this.quadrants.length === 0;
    this.error = '';
    try {
      const list: MatrixQuadrant[] = await Api.matrix();
      this.quadrants = list.map((q: MatrixQuadrant) => {
        const vm: QuadrantVM = {
          key: q.key,
          title: q.title,
          sub: q.sub,
          color: this.colorOf(q.key),
          bg: this.bgOf(q.key),
          tasks: wrapTasks(q.tasks),
        };
        return vm;
      });
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  private async toggle(task: TaskOut): Promise<void> {
    try {
      await Api.updateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' });
      await this.load();
      AppStore.syncReminders().catch(() => {
      });
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: '四象限',
        subtitle: '重要度决定上下，紧急度决定左右',
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
            ForEach(this.quadrants, (q: QuadrantVM) => {
              this.quadrantCard(q);
            }, (q: QuadrantVM) => `${q.key}-${q.tasks.length}`);
            Row().height(14);
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
  quadrantCard(q: QuadrantVM) {
    Column({ space: 6 }) {
      Row({ space: 8 }) {
        Row().width(4).height(18).backgroundColor(q.color).borderRadius(2);
        Column({ space: 1 }) {
          Text(q.title).fontSize(15).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT);
          Text(q.sub).fontSize(11).fontColor(Theme.TEXT_SUB);
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1);
        Text(`${q.tasks.length}`).fontSize(15).fontWeight(FontWeight.Bold).fontColor(q.color);
      }
      .width('100%');

      if (q.tasks.length === 0) {
        Text(this.emptyHintOf(q.key)).fontSize(11).fontColor(Theme.TEXT_WEAK);
      } else {
        ForEach(this.visibleTasks(q), (m: TaskItemModel) => {
          TaskItem({
            task: m,
            onToggle: (t: TaskOut) => {
              this.toggle(t);
            },
            onTap: (t: TaskOut) => {
              router.pushUrl({ url: 'pages/TaskEditPage', params: { taskId: t.id } });
            },
          });
        }, (m: TaskItemModel) => `${m.data.id}-${m.data.status}`);
        if (q.tasks.length > 3 && this.expanded !== q.key) {
          Text(`展开其余 ${q.tasks.length - 3} 项`)
            .fontSize(12)
            .fontColor(q.color)
            .onClick(() => {
              this.expanded = q.key;
            });
        } else if (this.expanded === q.key && q.tasks.length > 3) {
          Text('收起')
            .fontSize(12)
            .fontColor(Theme.TEXT_SUB)
            .onClick(() => {
              this.expanded = '';
            });
        }
      }
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
    .padding(13)
    .backgroundColor(q.bg)
    .borderRadius(Theme.RADIUS);
  }

  /** 默认只展示前 3 条：四个象限全展开会把「分布感」冲淡成一个长列表。 */
  private visibleTasks(q: QuadrantVM): TaskItemModel[] {
    return this.expanded === q.key ? q.tasks : q.tasks.slice(0, 3);
  }

  private emptyHintOf(key: string): string {
    if (key === 'q1') {
      return '很好，没有火烧眉毛的事';
    }
    if (key === 'q2') {
      return '这里空着才最危险——长期价值的事都在这个象限';
    }
    if (key === 'q3') {
      return '暂无可委托或可批量处理的琐事';
    }
    return '暂无可以直接删掉的事';
  }
}
