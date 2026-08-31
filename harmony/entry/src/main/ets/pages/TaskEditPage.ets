/**
 * 任务新建 / 编辑。
 *
 * 表单顺序按「填写频率」排：标题 → 维度 → 到期 → 目标/标签 → 高级项。
 * 只有标题是必填，其余都有合理默认值——录入摩擦越小，用户越愿意把事写进来。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import {
  CategoryOut,
  GoalOut,
  TagOut,
  TaskCreate,
  TaskOut,
  TaskUpdate,
} from '../common/Models';
import { Options, Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { Card, NavBar, SectionTitle, SegmentPicker } from '../view/Common';

interface TaskEditParams {
  taskId?: number;
  presetDate?: string;
  presetGoalId?: number;
}

@Entry
@Component
struct TaskEditPage {
  @State private taskId: number = 0;
  @State private loading: boolean = false;
  @State private saving: boolean = false;

  @State private title: string = '';
  @State private note: string = '';
  @State private categoryId: number = 0;
  @State private goalId: number = 0;
  @State private priority: string = 'normal';
  @State private importance: string = 'normal';
  @State private recurrence: string = 'none';
  @State private dueDate: string = '';
  @State private dueTime: string = '';
  @State private remindBefore: number = -1; // -1 = 跟随全局默认
  @State private tags: string[] = [];
  @State private status: string = 'todo';

  @State private categories: CategoryOut[] = [];
  @State private goals: GoalOut[] = [];
  @State private allTags: TagOut[] = [];
  @State private tagInput: string = '';
  @State private subtasks: TaskOut[] = [];

  aboutToAppear(): void {
    const params = router.getParams() as TaskEditParams;
    if (params?.presetDate) {
      this.dueDate = params.presetDate;
    }
    if (params?.presetGoalId) {
      this.goalId = params.presetGoalId;
    }
    this.taskId = params?.taskId ?? 0;
    this.load();
  }

  private async load(): Promise<void> {
    this.loading = true;
    try {
      this.categories = await AppStore.loadCategories();
      if (this.categoryId === 0 && this.categories.length > 0) {
        this.categoryId = this.categories[0].id;
      }
      this.goals = await Api.goals();
      this.allTags = await AppStore.loadTags();
      if (this.taskId > 0) {
        await this.loadTask();
      }
    } catch (err) {
      toast(errorText(err as object));
    } finally {
      this.loading = false;
    }
  }

  /**
   * 编辑态没有「取单条任务」的接口，用带筛选的列表接口取回。
   * 为一个纯前端便利去加一个后端接口并不划算，而 id 精确匹配的开销可忽略。
   */
  private async loadTask(): Promise<void> {
    const list: TaskOut[] = await Api.tasks({ limit: 500, status: 'all' });
    let found: TaskOut | null = null;
    const subs: TaskOut[] = [];
    for (const t of list) {
      if (t.id === this.taskId) {
        found = t;
      }
      if (t.parent_id === this.taskId) {
        subs.push(t);
      }
    }
    if (!found) {
      toast('任务不存在或已被删除');
      router.back();
      return;
    }
    this.title = found.title;
    this.note = found.note ?? '';
    this.categoryId = found.category_id;
    this.goalId = found.goal_id ?? 0;
    this.priority = found.priority;
    this.importance = found.importance;
    this.recurrence = found.recurrence;
    this.dueDate = found.due_date ?? '';
    this.dueTime = found.due_time ?? '';
    this.remindBefore = found.remind_before_minutes ?? -1;
    this.tags = found.tags.slice();
    this.status = found.status;
    this.subtasks = subs;
  }

  private addTag(name: string): void {
    const t: string = name.trim();
    if (t.length === 0 || this.tags.indexOf(t) >= 0) {
      return;
    }
    if (this.tags.length >= 20) {
      toast('单个任务最多 20 个标签');
      return;
    }
    this.tags = this.tags.concat([t]);
  }

  private removeTag(name: string): void {
    this.tags = this.tags.filter((t: string) => t !== name);
  }

  private commitTagInput(): void {
    // 支持一次粘贴多个：「阅读, 复盘 学习」都能拆开
    const parts: string[] = this.tagInput.split(/[,，\s]+/);
    for (const p of parts) {
      this.addTag(p);
    }
    this.tagInput = '';
  }

  private async save(): Promise<void> {
    if (this.title.trim().length === 0) {
      toast('请填写任务标题');
      return;
    }
    if (this.categoryId === 0) {
      toast('请选择所属维度');
      return;
    }
    this.saving = true;
    try {
      if (this.taskId > 0) {
        const body: TaskUpdate = {
          title: this.title.trim(),
          note: this.note.trim().length > 0 ? this.note.trim() : null,
          category_id: this.categoryId,
          goal_id: this.goalId > 0 ? this.goalId : null,
          priority: this.priority,
          importance: this.importance,
          recurrence: this.recurrence,
          due_date: this.dueDate.length > 0 ? this.dueDate : null,
          due_time: this.dueTime.length > 0 ? this.dueTime : null,
          remind_before_minutes: this.remindBefore >= 0 ? this.remindBefore : null,
          tags: this.tags,
        };
        await Api.updateTask(this.taskId, body);
      } else {
        const body: TaskCreate = {
          title: this.title.trim(),
          category_id: this.categoryId,
          note: this.note.trim().length > 0 ? this.note.trim() : null,
          goal_id: this.goalId > 0 ? this.goalId : null,
          priority: this.priority,
          importance: this.importance,
          recurrence: this.recurrence,
          due_date: this.dueDate.length > 0 ? this.dueDate : null,
          due_time: this.dueTime.length > 0 ? this.dueTime : null,
          remind_before_minutes: this.remindBefore >= 0 ? this.remindBefore : null,
          tags: this.tags,
        };
        await Api.createTask(body);
      }
      // 标签可能新建了：刷新缓存，让筛选面板立刻能看到
      AppStore.loadTags(true).catch(() => {
      });
      AppStore.syncReminders().catch(() => {
      });
      toast(this.taskId > 0 ? '已保存' : '已创建');
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
        title: '移入回收站',
        message: '任务将移入回收站，保留期内可恢复。',
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '移入', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.deleteTask(this.taskId);
        toast('已移入回收站');
        router.back();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  private pickDate(): void {
    const base: Date = this.dueDate.length > 0 ? DateUtil.parse(this.dueDate) : new Date();
    DatePickerDialog.show({
      selected: base,
      start: new Date(1970, 0, 1),
      end: new Date(2100, 11, 31),
      onDateAccept: (value: Date) => {
        this.dueDate = DateUtil.fmt(value);
      },
    });
  }

  private pickTime(): void {
    TimePickerDialog.show({
      selected: new Date(),
      useMilitaryTime: true,
      onAccept: (value: TimePickerResult) => {
        const h: string = value.hour < 10 ? `0${value.hour}` : `${value.hour}`;
        const m: string = value.minute < 10 ? `0${value.minute}` : `${value.minute}`;
        this.dueTime = `${h}:${m}`;
      },
    });
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: this.taskId > 0 ? '编辑任务' : '新建任务',
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
              this.basicSection();
            },
          });
          Card({
            content: () => {
              this.categorySection();
            },
          });
          Card({
            content: () => {
              this.dueSection();
            },
          });
          Card({
            content: () => {
              this.classifySection();
            },
          });
          Card({
            content: () => {
              this.tagSection();
            },
          });
          if (this.taskId > 0) {
            Card({
              content: () => {
                this.subtaskSection();
              },
            });
            Button('移入回收站')
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
      .fontColor(Theme.BRAND)
      .fontWeight(FontWeight.Medium)
      .onClick(() => {
        if (!this.saving) {
          this.save();
        }
      });
  }

  @Builder
  basicSection() {
    Column({ space: 10 }) {
      TextInput({ placeholder: '要做什么？', text: this.title })
        .height(46)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.title = v;
        });
      TextArea({ placeholder: '备注（可选）', text: this.note })
        .height(76)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.note = v;
        });
      if (this.taskId > 0) {
        Row({ space: 10 }) {
          Text(this.status === 'done' ? '已完成' : '进行中')
            .fontSize(13)
            .fontColor(this.status === 'done' ? Theme.OK : Theme.BRAND);
          Blank();
          Text(this.status === 'done' ? '标记为未完成' : '标记为完成')
            .fontSize(13)
            .fontColor(Theme.BRAND)
            .onClick(() => {
              this.status = this.status === 'done' ? 'todo' : 'done';
              Api.updateTask(this.taskId, { status: this.status })
                .then(() => {
                  toast(this.status === 'done' ? '已完成' : '已恢复待办');
                })
                .catch((e: object) => {
                  toastError(e);
                });
            });
        }
        .width('100%');
      }
    }
    .width('100%');
  }

  @Builder
  categorySection() {
    Column({ space: 8 }) {
      SectionTitle({ title: '所属维度' });
      Flex({ wrap: FlexWrap.Wrap }) {
        ForEach(this.categories, (c: CategoryOut) => {
          Text(`${c.icon} ${c.name}`)
            .fontSize(13)
            .fontColor(this.categoryId === c.id ? '#FFFFFF' : Theme.TEXT_SUB)
            .backgroundColor(this.categoryId === c.id ? c.color : '#F1F3F5')
            .borderRadius(9)
            .padding({ left: 11, right: 11, top: 6, bottom: 6 })
            .margin({ right: 8, bottom: 8 })
            .onClick(() => {
              this.categoryId = c.id;
            });
        }, (c: CategoryOut) => `${c.id}`);
      }
      .width('100%');

      SectionTitle({ title: '关联目标' });
      Flex({ wrap: FlexWrap.Wrap }) {
        Text('不关联')
          .fontSize(13)
          .fontColor(this.goalId === 0 ? '#FFFFFF' : Theme.TEXT_SUB)
          .backgroundColor(this.goalId === 0 ? Theme.TEXT_SUB : '#F1F3F5')
          .borderRadius(9)
          .padding({ left: 11, right: 11, top: 6, bottom: 6 })
          .margin({ right: 8, bottom: 8 })
          .onClick(() => {
            this.goalId = 0;
          });
        ForEach(this.goals, (g: GoalOut) => {
          Text(g.title)
            .fontSize(13)
            .fontColor(this.goalId === g.id ? '#FFFFFF' : Theme.PURPLE)
            .backgroundColor(this.goalId === g.id ? Theme.PURPLE : '#F5F3FF')
            .borderRadius(9)
            .padding({ left: 11, right: 11, top: 6, bottom: 6 })
            .margin({ right: 8, bottom: 8 })
            .constraintSize({ maxWidth: 200 })
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
            .onClick(() => {
              this.goalId = this.goalId === g.id ? 0 : g.id;
            });
        }, (g: GoalOut) => `${g.id}`);
      }
      .width('100%');
    }
    .width('100%');
  }

  @Builder
  dueSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '到期与提醒' });
      Row({ space: 8 }) {
        Text(this.dueDate.length > 0 ? this.dueDate : '选择日期')
          .fontSize(13)
          .fontColor(this.dueDate.length > 0 ? Theme.TEXT : Theme.TEXT_SUB)
          .backgroundColor('#F1F3F5')
          .borderRadius(9)
          .padding({ left: 12, right: 12, top: 8, bottom: 8 })
          .onClick(() => {
            this.pickDate();
          });
        Text(this.dueTime.length > 0 ? this.dueTime : '选择时间')
          .fontSize(13)
          .fontColor(this.dueTime.length > 0 ? Theme.TEXT : Theme.TEXT_SUB)
          .backgroundColor('#F1F3F5')
          .borderRadius(9)
          .padding({ left: 12, right: 12, top: 8, bottom: 8 })
          .onClick(() => {
            this.pickTime();
          });
        if (this.dueDate.length > 0 || this.dueTime.length > 0) {
          Text('清除')
            .fontSize(13)
            .fontColor(Theme.DANGER)
            .onClick(() => {
              this.dueDate = '';
              this.dueTime = '';
            });
        }
      }
      .width('100%');

      Row({ space: 8 }) {
        Text('今天').fontSize(12).fontColor(Theme.BRAND).onClick(() => {
          this.dueDate = DateUtil.today();
        });
        Text('明天').fontSize(12).fontColor(Theme.BRAND).onClick(() => {
          this.dueDate = DateUtil.addDays(DateUtil.today(), 1);
        });
        Text('本周末').fontSize(12).fontColor(Theme.BRAND).onClick(() => {
          const today: string = DateUtil.today();
          const dow: number = DateUtil.weekdayOf(today);
          this.dueDate = DateUtil.addDays(today, (6 - dow + 7) % 7);
        });
        Text('下周').fontSize(12).fontColor(Theme.BRAND).onClick(() => {
          this.dueDate = DateUtil.addDays(DateUtil.today(), 7);
        });
      }
      .width('100%');

      Text('提醒提前量').fontSize(12).fontColor(Theme.TEXT_SUB);
      Flex({ wrap: FlexWrap.Wrap }) {
        Text('跟随全局')
          .fontSize(12)
          .fontColor(this.remindBefore < 0 ? '#FFFFFF' : Theme.TEXT_SUB)
          .backgroundColor(this.remindBefore < 0 ? Theme.BRAND : '#F1F3F5')
          .borderRadius(8)
          .padding({ left: 10, right: 10, top: 5, bottom: 5 })
          .margin({ right: 7, bottom: 7 })
          .onClick(() => {
            this.remindBefore = -1;
          });
        ForEach(Options.REMIND_MINUTES, (m: number) => {
          Text(Options.remindLabel(m))
            .fontSize(12)
            .fontColor(this.remindBefore === m ? '#FFFFFF' : Theme.TEXT_SUB)
            .backgroundColor(this.remindBefore === m ? Theme.BRAND : '#F1F3F5')
            .borderRadius(8)
            .padding({ left: 10, right: 10, top: 5, bottom: 5 })
            .margin({ right: 7, bottom: 7 })
            .onClick(() => {
              this.remindBefore = m;
            });
        }, (m: number) => `${m}`);
      }
      .width('100%');

      Text('重复').fontSize(12).fontColor(Theme.TEXT_SUB);
      Flex({ wrap: FlexWrap.Wrap }) {
        ForEach(Options.RECURRENCES, (r: string) => {
          Text(Theme.recurrenceLabel(r))
            .fontSize(12)
            .fontColor(this.recurrence === r ? '#FFFFFF' : Theme.TEXT_SUB)
            .backgroundColor(this.recurrence === r ? Theme.BRAND : '#F1F3F5')
            .borderRadius(8)
            .padding({ left: 10, right: 10, top: 5, bottom: 5 })
            .margin({ right: 7, bottom: 7 })
            .onClick(() => {
              this.recurrence = r;
            });
        }, (r: string) => r);
      }
      .width('100%');
      if (this.recurrence !== 'none' && this.dueDate.length === 0) {
        Text('重复任务需要设置到期日才会生成下一次')
          .fontSize(11)
          .fontColor(Theme.WARN);
      }
    }
    .width('100%');
  }

  @Builder
  classifySection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '重要度（决定四象限的上下）' });
      SegmentPicker({
        labels: ['次要', '一般', '重要'],
        values: Options.IMPORTANCES,
        selected: this.importance,
        onSelect: (v: string) => {
          this.importance = v;
        },
      });
      SectionTitle({ title: '紧急度（决定四象限的左右）' });
      SegmentPicker({
        labels: ['不急', '一般', '较急', '紧急'],
        values: Options.PRIORITIES,
        selected: this.priority,
        onSelect: (v: string) => {
          this.priority = v;
        },
      });
      Text(this.quadrantHint())
        .fontSize(11)
        .fontColor(Theme.TEXT_SUB);
    }
    .width('100%');
  }

  /** 实时告诉用户当前组合会落进哪个象限，避免「填完不知道去哪了」。 */
  private quadrantHint(): string {
    const important: boolean = this.importance === 'high';
    const urgent: boolean = this.priority === 'urgent' || this.priority === 'high';
    if (important && urgent) {
      return '当前会进入「重要且紧急 · 立刻做」';
    }
    if (important) {
      return '当前会进入「重要不紧急 · 计划做」';
    }
    if (urgent) {
      return '当前会进入「紧急不重要 · 委托做」';
    }
    return '当前会进入「不重要不紧急 · 少做」';
  }

  @Builder
  tagSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '标签' });
      if (this.tags.length > 0) {
        Flex({ wrap: FlexWrap.Wrap }) {
          ForEach(this.tags, (t: string) => {
            Text(`#${t} ✕`)
              .fontSize(12)
              .fontColor('#FFFFFF')
              .backgroundColor(AppStore.tagColor(t))
              .borderRadius(8)
              .padding({ left: 9, right: 9, top: 5, bottom: 5 })
              .margin({ right: 7, bottom: 7 })
              .onClick(() => {
                this.removeTag(t);
              });
          }, (t: string) => t);
        }
        .width('100%');
      }
      Row({ space: 8 }) {
        TextInput({ placeholder: '输入标签后点「添加」', text: this.tagInput })
          .height(38)
          .layoutWeight(1)
          .borderRadius(9)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.tagInput = v;
          })
          .onSubmit(() => {
            this.commitTagInput();
          });
        Button('添加')
          .fontSize(13)
          .height(34)
          .backgroundColor('#EEF2FF')
          .fontColor(Theme.BRAND_DARK)
          .onClick(() => {
            this.commitTagInput();
          });
      }
      .width('100%');

      if (this.allTags.length > 0) {
        Text('已有标签').fontSize(11).fontColor(Theme.TEXT_WEAK);
        Flex({ wrap: FlexWrap.Wrap }) {
          ForEach(this.allTags, (t: TagOut) => {
            Text(`#${t.name}`)
              .fontSize(12)
              .fontColor(t.color)
              .backgroundColor('#F5F6F8')
              .borderRadius(8)
              .padding({ left: 9, right: 9, top: 5, bottom: 5 })
              .margin({ right: 7, bottom: 7 })
              .onClick(() => {
                this.addTag(t.name);
              });
          }, (t: TagOut) => `${t.id}`);
        }
        .width('100%');
      }
    }
    .width('100%');
  }

  @Builder
  subtaskSection() {
    Column({ space: 8 }) {
      SectionTitle({ title: `子任务（${this.subtasks.length}）` });
      if (this.subtasks.length === 0) {
        Text('把大任务拆成 2-5 个可在一次专注内完成的小步骤，完成率会明显提高')
          .fontSize(11)
          .fontColor(Theme.TEXT_WEAK);
      } else {
        ForEach(this.subtasks, (s: TaskOut) => {
          Row({ space: 8 }) {
            Text(s.status === 'done' ? '✓' : '○')
              .fontSize(13)
              .fontColor(s.status === 'done' ? Theme.OK : Theme.TEXT_WEAK);
            Text(s.title)
              .fontSize(13)
              .fontColor(s.status === 'done' ? Theme.TEXT_WEAK : Theme.TEXT)
              .layoutWeight(1)
              .maxLines(1)
              .textOverflow({ overflow: TextOverflow.Ellipsis });
          }
          .width('100%')
          .padding({ top: 6, bottom: 6 })
          .onClick(() => {
            router.pushUrl({ url: 'pages/TaskEditPage', params: { taskId: s.id } });
          });
        }, (s: TaskOut) => `${s.id}-${s.status}`);
      }
    }
    .width('100%');
  }
}
