/**
 * 目标详情 / 编辑：基本信息 + 关联任务 + 完成度。
 *
 * 「关联任务」直接在本页展示并可勾选，这样目标不只是一个标题，
 * 而是一个能推进的工作台——否则用户建完目标就再也不会打开它。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import { GoalCreate, GoalOut, GoalUpdate, TaskOut } from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import {
  Card,
  EmptyTip,
  NavBar,
  ProgressBar,
  SectionTitle,
  SegmentPicker,
} from '../view/Common';
import { TaskItem, TaskItemModel, wrapTasks } from '../view/TaskItem';

interface GoalEditParams {
  goalId?: number;
}

@Entry
@Component
struct GoalEditPage {
  @State private goalId: number = 0;
  @State private title: string = '';
  @State private description: string = '';
  @State private deadline: string = '';
  @State private status: string = 'active';
  @State private saving: boolean = false;
  @State private tasks: TaskItemModel[] = [];
  @State private loaded: boolean = false;

  aboutToAppear(): void {
    const params = router.getParams() as GoalEditParams;
    this.goalId = params?.goalId ?? 0;
    this.load();
  }

  onPageShow(): void {
    if (this.goalId > 0 && this.loaded) {
      this.loadTasks();
    }
  }

  private async load(): Promise<void> {
    if (this.goalId === 0) {
      this.loaded = true;
      return;
    }
    try {
      const goals: GoalOut[] = await Api.goals();
      const found: GoalOut | undefined = goals.find((g: GoalOut) => g.id === this.goalId);
      if (!found) {
        toast('目标不存在');
        router.back();
        return;
      }
      this.title = found.title;
      this.description = found.description ?? '';
      this.deadline = found.deadline ?? '';
      this.status = found.status;
      await this.loadTasks();
    } catch (err) {
      toast(errorText(err as object));
    } finally {
      this.loaded = true;
    }
  }

  private async loadTasks(): Promise<void> {
    try {
      const list: TaskOut[] = await Api.tasks({
        goal_id: this.goalId,
        status: 'all',
        sort: 'due',
        limit: 200,
      });
      this.tasks = wrapTasks(list);
    } catch (e) {
      // 任务列表失败不阻塞目标信息的展示
    }
  }

  private doneCount(): number {
    let n: number = 0;
    for (const m of this.tasks) {
      if (m.data.status === 'done') {
        n++;
      }
    }
    return n;
  }

  private progress(): number {
    if (this.tasks.length === 0) {
      return 0;
    }
    return Math.round((this.doneCount() / this.tasks.length) * 100);
  }

  private pickDeadline(): void {
    DatePickerDialog.show({
      selected: this.deadline.length > 0 ? DateUtil.parse(this.deadline) : new Date(),
      start: new Date(1970, 0, 1),
      end: new Date(2100, 11, 31),
      onDateAccept: (value: Date) => {
        this.deadline = DateUtil.fmt(value);
      },
    });
  }

  private async save(): Promise<void> {
    if (this.title.trim().length === 0) {
      toast('请填写目标标题');
      return;
    }
    this.saving = true;
    try {
      if (this.goalId > 0) {
        const body: GoalUpdate = {
          title: this.title.trim(),
          description: this.description.trim().length > 0 ? this.description.trim() : null,
          deadline: this.deadline.length > 0 ? this.deadline : null,
          status: this.status,
        };
        await Api.updateGoal(this.goalId, body);
      } else {
        const body: GoalCreate = {
          title: this.title.trim(),
          description: this.description.trim().length > 0 ? this.description.trim() : null,
          deadline: this.deadline.length > 0 ? this.deadline : null,
        };
        await Api.createGoal(body);
      }
      toast('已保存');
      router.back();
    } catch (err) {
      toastError(err as object);
    } finally {
      this.saving = false;
    }
  }

  private async remove(): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '删除目标',
        message: '删除后关联任务会保留，但不再归属任何目标。该操作不可撤销。',
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '删除', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.deleteGoal(this.goalId);
        toast('已删除');
        router.back();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  private async toggleTask(task: TaskOut): Promise<void> {
    try {
      await Api.updateTask(task.id, { status: task.status === 'done' ? 'todo' : 'done' });
      await this.loadTasks();
      AppStore.syncReminders().catch(() => {
      });
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: this.goalId > 0 ? '目标详情' : '新建目标',
        onBack: () => {
          router.back();
        },
        trailing: () => {
          this.navActions();
        },
      });
      Scroll() {
        Column({ space: Theme.GAP }) {
          Card({
            content: () => {
              this.formSection();
            },
          });
          if (this.goalId > 0) {
            Card({
              content: () => {
                this.progressSection();
              },
            });
            Card({
              content: () => {
                this.taskSection();
              },
            });
            Button('删除目标')
              .width('100%')
              .height(42)
              .borderRadius(12)
              .backgroundColor('#FEE2E2')
              .fontColor(Theme.DANGER)
              .onClick(() => {
                this.remove();
              });
          }
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
  navActions() {
    Text(this.saving ? '保存中' : '保存')
      .fontSize(15)
      .fontColor(Theme.PURPLE)
      .fontWeight(FontWeight.Medium)
      .onClick(() => {
        if (!this.saving) {
          this.save();
        }
      });
  }

  @Builder
  formSection() {
    Column({ space: 10 }) {
      TextInput({ placeholder: '目标标题，如「今年读完 12 本书」', text: this.title })
        .height(46)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.title = v;
        });
      TextArea({ placeholder: '为什么要做这件事？（可选）', text: this.description })
        .height(76)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.description = v;
        });
      Row({ space: 8 }) {
        Text(this.deadline.length > 0 ? `截止 ${this.deadline}` : '设置截止日期')
          .fontSize(13)
          .fontColor(this.deadline.length > 0 ? Theme.TEXT : Theme.TEXT_SUB)
          .backgroundColor('#F1F3F5')
          .borderRadius(9)
          .padding({ left: 12, right: 12, top: 8, bottom: 8 })
          .onClick(() => {
            this.pickDeadline();
          });
        if (this.deadline.length > 0) {
          Text('清除').fontSize(13).fontColor(Theme.DANGER).onClick(() => {
            this.deadline = '';
          });
        }
      }
      .width('100%');
      if (this.goalId > 0) {
        SectionTitle({ title: '状态' });
        SegmentPicker({
          labels: ['进行中', '已完成', '已归档'],
          values: ['active', 'done', 'archived'],
          selected: this.status,
          onSelect: (v: string) => {
            this.status = v;
          },
        });
      }
    }
    .width('100%');
  }

  @Builder
  progressSection() {
    Column({ space: 8 }) {
      Row() {
        Text('完成度').fontSize(14).fontColor(Theme.TEXT).layoutWeight(1);
        Text(`${this.progress()}%`)
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.PURPLE);
      }
      .width('100%');
      ProgressBar({ percent: this.progress(), color: Theme.PURPLE });
      Text(`共 ${this.tasks.length} 项任务，已完成 ${this.doneCount()} 项`)
        .fontSize(11)
        .fontColor(Theme.TEXT_SUB);
    }
    .width('100%');
  }

  @Builder
  taskSection() {
    Column({ space: 4 }) {
      SectionTitle({
        title: '关联任务',
        action: '＋ 添加',
        onAction: () => {
          router.pushUrl({
            url: 'pages/TaskEditPage',
            params: { presetGoalId: this.goalId },
          });
        },
      });
      if (this.tasks.length === 0) {
        EmptyTip({
          text: '还没有关联任务',
          hint: '把目标拆成具体动作，才可能真的完成',
        });
      } else {
        ForEach(this.tasks, (m: TaskItemModel) => {
          Column() {
            TaskItem({
              task: m,
              onToggle: (t: TaskOut) => {
                this.toggleTask(t);
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
}
