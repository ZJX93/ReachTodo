/**
 * 任务行。任务列表、四象限、日详情、目标详情共用同一个渲染，
 * 保证「同一条任务在任何页面看起来都一样」。
 */
import { DateUtil } from '../common/DateUtil';
import { TaskOut } from '../common/Models';
import { Theme } from '../common/Theme';
import { Chip } from './Common';

@Component
export struct TaskItem {
  @ObjectLink task: TaskItemModel;
  showCategory: boolean = true;
  selectable: boolean = false;
  selected: boolean = false;
  onToggle: (task: TaskOut) => void = () => {
  };
  onTap: (task: TaskOut) => void = () => {
  };
  onLongPress: (task: TaskOut) => void = () => {
  };

  build() {
    Row({ space: 10 }) {
      // 勾选圈：批量模式下变为多选框
      Stack() {
        Circle()
          .width(21)
          .height(21)
          .fill(this.checkedFill())
          .stroke(this.checkedStroke())
          .strokeWidth(1.6);
        if (this.isChecked()) {
          Text('✓').fontSize(12).fontColor('#FFFFFF');
        }
      }
      .width(21)
      .height(21)
      .onClick(() => {
        this.onToggle(this.task.data);
      });

      Column({ space: 5 }) {
        Text(this.task.data.title)
          .fontSize(15)
          .fontColor(this.task.data.status === 'done' ? Theme.TEXT_WEAK : Theme.TEXT)
          .decoration({
            type: this.task.data.status === 'done'
              ? TextDecorationType.LineThrough
              : TextDecorationType.None,
          })
          .maxLines(2)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%');

        if (this.hasMeta()) {
          Flex({ wrap: FlexWrap.Wrap }) {
            if (this.task.data.due_date) {
              Text(this.dueText())
                .fontSize(11)
                .fontColor(DateUtil.isOverdue(this.task.data.due_date) &&
                  this.task.data.status === 'todo' ? Theme.DANGER : Theme.TEXT_SUB)
                .margin({ right: 8, top: 2 });
            }
            if (this.showCategory && this.task.data.category_name) {
              Text(`${this.task.data.category_icon ?? ''}${this.task.data.category_name}`)
                .fontSize(11)
                .fontColor(this.task.data.category_color ?? Theme.TEXT_SUB)
                .margin({ right: 8, top: 2 });
            }
            if (this.task.data.goal_title) {
              Text(`◎${this.task.data.goal_title}`)
                .fontSize(11)
                .fontColor(Theme.PURPLE)
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
                .constraintSize({ maxWidth: 120 })
                .margin({ right: 8, top: 2 });
            }
            if (this.task.data.recurrence !== 'none') {
              Text(`↻${Theme.recurrenceLabel(this.task.data.recurrence)}`)
                .fontSize(11)
                .fontColor(Theme.TEXT_SUB)
                .margin({ right: 8, top: 2 });
            }
            ForEach(this.task.data.tags, (t: string) => {
              Text(`#${t}`)
                .fontSize(11)
                .fontColor(Theme.BRAND)
                .margin({ right: 6, top: 2 });
            }, (t: string) => t);
          }
          .width('100%');
        }
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start);

      // 右侧紧急度色条：重要度用「重」字标注，不占宽度
      Column({ space: 4 }) {
        if (this.task.data.importance === 'high') {
          Chip({ text: '重要', color: Theme.DANGER });
        }
        Row()
          .width(4)
          .height(20)
          .backgroundColor(Theme.priorityColor(this.task.data.priority))
          .borderRadius(2);
      }
      .alignItems(HorizontalAlign.End);
    }
    .width('100%')
    .alignItems(VerticalAlign.Top)
    .padding({ top: 11, bottom: 11 })
    .onClick(() => {
      this.onTap(this.task.data);
    })
    .gesture(
      LongPressGesture().onAction(() => {
        this.onLongPress(this.task.data);
      })
    );
  }

  private isChecked(): boolean {
    return this.selectable ? this.selected : this.task.data.status === 'done';
  }

  private checkedFill(): string {
    return this.isChecked() ? Theme.BRAND : '#00000000';
  }

  private checkedStroke(): string {
    return this.isChecked() ? Theme.BRAND : Theme.BORDER;
  }

  private hasMeta(): boolean {
    const d = this.task.data;
    return !!d.due_date || !!d.category_name || !!d.goal_title ||
      d.recurrence !== 'none' || d.tags.length > 0;
  }

  private dueText(): string {
    const d = this.task.data;
    const day: string = DateUtil.humanDue(d.due_date);
    return d.due_time ? `${day} ${d.due_time}` : day;
  }
}

/**
 * 包装类。
 *
 * ArkUI 的 `ForEach` + 对象数组若直接绑定 interface，改动单条属性不会触发重绘；
 * 用 `@Observed` 类包一层再配 `@ObjectLink`，即可做到「只重绘变化的那一行」，
 * 在几百条任务的列表里差别非常明显。
 */
@Observed
export class TaskItemModel {
  data: TaskOut;

  constructor(data: TaskOut) {
    this.data = data;
  }
}

/** 批量把接口数据转成可观察模型。 */
export function wrapTasks(list: TaskOut[]): TaskItemModel[] {
  return list.map((t: TaskOut) => new TaskItemModel(t));
}
