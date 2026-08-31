/**
 * 任务页：搜索 + 多维筛选 + 批量操作。
 *
 * 筛选条件全部下推到服务端（`GET /api/tasks` 的 q/tag/status/...），
 * 而不是「全量拉回本地再 filter」。任务量上千后本地筛选会明显卡顿，
 * 且分页与本地筛选天生冲突。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import {
  CategoryOut,
  TagOut,
  TaskBulkRequest,
  TaskBulkResult,
  TaskOut,
  TaskQuery,
} from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { EmptyTip, SegmentPicker, StateHint } from './Common';
import { TaskItem, TaskItemModel, wrapTasks } from './TaskItem';

@Component
export struct TasksView {
  @Link @Watch('onRefreshKeyChange') refreshKey: number;

  @State private loading: boolean = true;
  @State private error: string = '';
  @State private tasks: TaskItemModel[] = [];

  // 筛选状态
  @State private keyword: string = '';
  @State private status: string = 'todo';
  @State private categoryId: number = 0;      // 0 = 全部
  @State private activeTag: string = '';
  @State private sort: string = 'default';
  @State private onlyOverdue: boolean = false;
  @State private showFilter: boolean = false;

  @State private categories: CategoryOut[] = [];
  @State private tags: TagOut[] = [];

  // 批量模式
  @State private bulkMode: boolean = false;
  @State private selectedIds: number[] = [];

  private searchTimer: number = -1;

  aboutToAppear(): void {
    this.status = AppStore.settings().showCompleted ? 'all' : 'todo';
    this.loadMeta();
    this.load();
  }

  onRefreshKeyChange(): void {
    this.load();
  }

  private async loadMeta(): Promise<void> {
    try {
      this.categories = await AppStore.loadCategories();
      this.tags = await AppStore.loadTags();
    } catch (err) {
      // 元数据失败不影响列表本身，静默即可
    }
  }

  private buildQuery(): TaskQuery {
    const q: TaskQuery = { limit: 300, top_level: true };
    if (this.keyword.trim().length > 0) {
      q.q = this.keyword.trim();
    }
    if (this.status !== 'all') {
      q.status = this.status;
    }
    if (this.categoryId > 0) {
      q.category_id = this.categoryId;
    }
    if (this.activeTag.length > 0) {
      q.tag = [this.activeTag];
    }
    if (this.sort !== 'default') {
      q.sort = this.sort;
    }
    if (this.onlyOverdue) {
      q.overdue = true;
    }
    return q;
  }

  private async load(): Promise<void> {
    this.loading = this.tasks.length === 0;
    this.error = '';
    try {
      const list: TaskOut[] = await Api.tasks(this.buildQuery());
      this.tasks = wrapTasks(list);
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  /**
   * 搜索防抖 300ms。
   * 不防抖的话每敲一个字就打一次接口，中文输入法在候选阶段还会触发多次。
   */
  private onKeywordChange(v: string): void {
    this.keyword = v;
    if (this.searchTimer !== -1) {
      clearTimeout(this.searchTimer);
    }
    this.searchTimer = setTimeout(() => {
      this.searchTimer = -1;
      this.load();
    }, 300);
  }

  private async toggle(task: TaskOut): Promise<void> {
    if (this.bulkMode) {
      this.toggleSelect(task.id);
      return;
    }
    try {
      await Api.updateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' });
      await this.load();
      AppStore.syncReminders().catch(() => {
      });
    } catch (err) {
      toastError(err as object);
    }
  }

  private toggleSelect(id: number): void {
    const idx: number = this.selectedIds.indexOf(id);
    const next: number[] = this.selectedIds.slice();
    if (idx >= 0) {
      next.splice(idx, 1);
    } else {
      next.push(id);
    }
    this.selectedIds = next;
  }

  private isSelected(id: number): boolean {
    return this.selectedIds.indexOf(id) >= 0;
  }

  private exitBulk(): void {
    this.bulkMode = false;
    this.selectedIds = [];
  }

  private async runBulk(action: string): Promise<void> {
    if (this.selectedIds.length === 0) {
      toast('请先选择任务');
      return;
    }
    const body: TaskBulkRequest = { ids: this.selectedIds, action: action };
    try {
      const res: TaskBulkResult = await Api.bulkTasks(body);
      toast(`已处理 ${res.affected} 项${res.skipped > 0 ? `，跳过 ${res.skipped} 项` : ''}`);
      this.exitBulk();
      await this.load();
      AppStore.syncReminders().catch(() => {
      });
    } catch (err) {
      toastError(err as object);
    }
  }

  private async deleteTask(task: TaskOut): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '移入回收站',
        message: `「${task.title}」将移入回收站，可在「我的 → 回收站」恢复。`,
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '移入', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.deleteTask(task.id);
        toast('已移入回收站');
        await this.load();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Stack({ alignContent: Alignment.BottomEnd }) {
      Column({ space: 0 }) {
        this.searchBar();
        if (this.showFilter) {
          this.filterPanel();
        }
        if (this.bulkMode) {
          this.bulkBar();
        }
        this.listArea();
      }
      .width('100%')
      .height('100%');

      if (!this.bulkMode) {
        Button('＋')
          .width(54)
          .height(54)
          .borderRadius(27)
          .fontSize(26)
          .backgroundColor(Theme.BRAND)
          .margin({ right: 18, bottom: 20 })
          .onClick(() => {
            router.pushUrl({ url: 'pages/TaskEditPage' });
          });
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  searchBar() {
    Row({ space: 8 }) {
      TextInput({ placeholder: '搜索标题或备注', text: this.keyword })
        .height(38)
        .layoutWeight(1)
        .borderRadius(10)
        .backgroundColor('#F1F3F5')
        .onChange((v: string) => {
          this.onKeywordChange(v);
        });
      Text(this.showFilter ? '收起' : '筛选')
        .fontSize(13)
        .fontColor(this.hasFilter() ? Theme.BRAND : Theme.TEXT_SUB)
        .onClick(() => {
          this.showFilter = !this.showFilter;
        });
      Text(this.bulkMode ? '取消' : '多选')
        .fontSize(13)
        .fontColor(Theme.TEXT_SUB)
        .onClick(() => {
          if (this.bulkMode) {
            this.exitBulk();
          } else {
            this.bulkMode = true;
          }
        });
    }
    .width('100%')
    .padding({ left: 14, right: 14, top: 10, bottom: 10 })
    .backgroundColor(Theme.CARD);
  }

  private hasFilter(): boolean {
    return this.categoryId > 0 || this.activeTag.length > 0 ||
      this.onlyOverdue || this.sort !== 'default' || this.status !== 'todo';
  }

  @Builder
  filterPanel() {
    Column({ space: 10 }) {
      SegmentPicker({
        labels: ['待办', '已完成', '全部'],
        values: ['todo', 'done', 'all'],
        selected: this.status,
        onSelect: (v: string) => {
          this.status = v;
          this.load();
        },
      });

      Scroll() {
        Row({ space: 6 }) {
          Text('全部维度')
            .fontSize(12)
            .fontColor(this.categoryId === 0 ? '#FFFFFF' : Theme.TEXT_SUB)
            .backgroundColor(this.categoryId === 0 ? Theme.BRAND : '#F1F3F5')
            .borderRadius(8)
            .padding({ left: 10, right: 10, top: 5, bottom: 5 })
            .onClick(() => {
              this.categoryId = 0;
              this.load();
            });
          ForEach(this.categories, (c: CategoryOut) => {
            Text(`${c.icon}${c.name}`)
              .fontSize(12)
              .fontColor(this.categoryId === c.id ? '#FFFFFF' : Theme.TEXT_SUB)
              .backgroundColor(this.categoryId === c.id ? c.color : '#F1F3F5')
              .borderRadius(8)
              .padding({ left: 10, right: 10, top: 5, bottom: 5 })
              .onClick(() => {
                this.categoryId = this.categoryId === c.id ? 0 : c.id;
                this.load();
              });
          }, (c: CategoryOut) => `${c.id}`);
        }
      }
      .scrollable(ScrollDirection.Horizontal)
      .scrollBar(BarState.Off)
      .width('100%');

      if (this.tags.length > 0) {
        Scroll() {
          Row({ space: 6 }) {
            ForEach(this.tags, (t: TagOut) => {
              Text(`#${t.name}`)
                .fontSize(12)
                .fontColor(this.activeTag === t.name ? '#FFFFFF' : t.color)
                .backgroundColor(this.activeTag === t.name ? t.color : '#F1F3F5')
                .borderRadius(8)
                .padding({ left: 10, right: 10, top: 5, bottom: 5 })
                .onClick(() => {
                  this.activeTag = this.activeTag === t.name ? '' : t.name;
                  this.load();
                });
            }, (t: TagOut) => `${t.id}`);
          }
        }
        .scrollable(ScrollDirection.Horizontal)
        .scrollBar(BarState.Off)
        .width('100%');
      }

      Row({ space: 12 }) {
        Text(this.onlyOverdue ? '☑ 只看逾期' : '☐ 只看逾期')
          .fontSize(12)
          .fontColor(this.onlyOverdue ? Theme.DANGER : Theme.TEXT_SUB)
          .onClick(() => {
            this.onlyOverdue = !this.onlyOverdue;
            this.load();
          });
        Text('排序：').fontSize(12).fontColor(Theme.TEXT_SUB);
        ForEach(['default', 'due', 'priority', 'created'], (s: string) => {
          Text(this.sortLabel(s))
            .fontSize(12)
            .fontColor(this.sort === s ? Theme.BRAND : Theme.TEXT_SUB)
            .onClick(() => {
              this.sort = s;
              this.load();
            });
        }, (s: string) => s);
      }
      .width('100%');
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
    .padding({ left: 14, right: 14, top: 4, bottom: 12 })
    .backgroundColor(Theme.CARD)
    .border({ width: { bottom: 1 }, color: Theme.BORDER });
  }

  private sortLabel(s: string): string {
    if (s === 'due') {
      return '按到期';
    }
    if (s === 'priority') {
      return '按紧急';
    }
    if (s === 'created') {
      return '按创建';
    }
    return '默认';
  }

  @Builder
  bulkBar() {
    Row({ space: 10 }) {
      Text(`已选 ${this.selectedIds.length}`).fontSize(13).fontColor(Theme.TEXT);
      Text('全选')
        .fontSize(13)
        .fontColor(Theme.BRAND)
        .onClick(() => {
          this.selectedIds = this.tasks.map((m: TaskItemModel) => m.data.id);
        });
      Blank();
      Text('完成')
        .fontSize(13)
        .fontColor(Theme.OK)
        .onClick(() => {
          this.runBulk('complete');
        });
      Text('恢复待办')
        .fontSize(13)
        .fontColor(Theme.BRAND)
        .onClick(() => {
          this.runBulk('reopen');
        });
      Text('删除')
        .fontSize(13)
        .fontColor(Theme.DANGER)
        .onClick(() => {
          this.runBulk('delete');
        });
    }
    .width('100%')
    .padding({ left: 14, right: 14, top: 10, bottom: 10 })
    .backgroundColor('#FFF7ED');
  }

  @Builder
  listArea() {
    if (this.loading || this.error.length > 0) {
      StateHint({
        loading: this.loading,
        error: this.error,
        onRetry: () => {
          this.load();
        },
      });
    } else if (this.tasks.length === 0) {
      EmptyTip({
        text: '没有符合条件的任务',
        hint: this.hasFilter() || this.keyword.length > 0
          ? '试试放宽筛选条件'
          : '点右下角「＋」新建第一个任务',
      });
    } else {
      List({ space: 0 }) {
        ForEach(this.tasks, (m: TaskItemModel) => {
          ListItem() {
            Column() {
              TaskItem({
                task: m,
                selectable: this.bulkMode,
                selected: this.isSelected(m.data.id),
                onToggle: (t: TaskOut) => {
                  this.toggle(t);
                },
                onTap: (t: TaskOut) => {
                  if (this.bulkMode) {
                    this.toggleSelect(t.id);
                  } else {
                    router.pushUrl({ url: 'pages/TaskEditPage', params: { taskId: t.id } });
                  }
                },
                onLongPress: (t: TaskOut) => {
                  if (!this.bulkMode) {
                    this.deleteTask(t);
                  }
                },
              });
              Divider().color(Theme.BORDER).strokeWidth(0.5);
            }
            .width('100%');
          }
        }, (m: TaskItemModel) => `${m.data.id}-${m.data.status}-${m.data.title}`);
      }
      .width('100%')
      .layoutWeight(1)
      .padding({ left: 14, right: 14 })
      .backgroundColor(Theme.CARD)
      .scrollBar(BarState.Off);
    }
  }
}
