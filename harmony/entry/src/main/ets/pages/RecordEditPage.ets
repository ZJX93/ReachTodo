/**
 * 记录新建 / 编辑。
 *
 * 按类型动态显示字段：读书笔记才问书名作者，工作日志才问项目。
 * 一次性把所有字段摊开会让「随手记一句」变成填表格，
 * 而随手记正是记录功能最高频的用法。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import { RecordCreate, RecordOut, RecordUpdate, TemplateOut } from '../common/Models';
import { Options, Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { Card, NavBar, SectionTitle, SegmentPicker } from '../view/Common';

interface RecordEditParams {
  recordId?: number;
  presetDate?: string;
  presetType?: string;
}

const MOODS: string[] = ['😀', '🙂', '😐', '😕', '😫', '💪', '🎯', '📚'];

@Entry
@Component
struct RecordEditPage {
  @State private recordId: number = 0;
  @State private type: string = 'diary';
  @State private title: string = '';
  @State private content: string = '';
  @State private mood: string = '';
  @State private tags: string = '';
  @State private bookTitle: string = '';
  @State private bookAuthor: string = '';
  @State private project: string = '';
  @State private recordDate: string = '';
  @State private recordTime: string = '';
  @State private saving: boolean = false;
  @State private templates: TemplateOut[] = [];

  aboutToAppear(): void {
    const params = router.getParams() as RecordEditParams;
    this.recordId = params?.recordId ?? 0;
    this.recordDate = params?.presetDate ?? DateUtil.today();
    if (params?.presetType) {
      this.type = params.presetType;
    }
    this.load();
  }

  private async load(): Promise<void> {
    try {
      this.templates = await Api.templates();
    } catch (e) {
      // 模板是可选增强
    }
    if (this.recordId === 0) {
      return;
    }
    try {
      // 记录同样没有「取单条」接口，用日期定位后精确匹配 id
      const list: RecordOut[] = await Api.records({ limit: 500 });
      const found: RecordOut | undefined = list.find((r: RecordOut) => r.id === this.recordId);
      if (!found) {
        toast('记录不存在或已被删除');
        router.back();
        return;
      }
      this.type = found.type;
      this.title = found.title;
      this.content = found.content ?? '';
      this.mood = found.mood ?? '';
      this.tags = found.tags ?? '';
      this.bookTitle = found.book_title ?? '';
      this.bookAuthor = found.book_author ?? '';
      this.project = found.project ?? '';
      this.recordDate = found.record_date;
      this.recordTime = found.record_time ?? '';
    } catch (err) {
      toast(errorText(err as object));
    }
  }

  private applyTemplate(t: TemplateOut): void {
    this.type = t.type;
    if (this.content.trim().length === 0) {
      this.content = t.content ?? '';
    } else {
      // 已有内容时追加而不是覆盖，避免误触丢失已写内容
      this.content = `${this.content}\n\n${t.content ?? ''}`;
    }
    if (this.title.trim().length === 0) {
      this.title = t.name;
    }
    toast(`已套用模板「${t.name}」`);
  }

  private pickDate(): void {
    DatePickerDialog.show({
      selected: DateUtil.parse(this.recordDate),
      start: new Date(1970, 0, 1),
      end: new Date(2100, 11, 31),
      onDateAccept: (value: Date) => {
        this.recordDate = DateUtil.fmt(value);
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
        this.recordTime = `${h}:${m}`;
      },
    });
  }

  private async save(): Promise<void> {
    if (this.content.trim().length === 0 && this.title.trim().length === 0) {
      toast('写点什么吧');
      return;
    }
    this.saving = true;
    try {
      if (this.recordId > 0) {
        const body: RecordUpdate = {
          type: this.type,
          title: this.title.trim().length > 0 ? this.title.trim() : null,
          content: this.content.trim().length > 0 ? this.content.trim() : null,
          mood: this.mood.length > 0 ? this.mood : null,
          tags: this.tags.trim().length > 0 ? this.tags.trim() : null,
          book_title: this.bookTitle.trim().length > 0 ? this.bookTitle.trim() : null,
          book_author: this.bookAuthor.trim().length > 0 ? this.bookAuthor.trim() : null,
          project: this.project.trim().length > 0 ? this.project.trim() : null,
          record_date: this.recordDate,
          record_time: this.recordTime.length > 0 ? this.recordTime : null,
        };
        await Api.updateRecord(this.recordId, body);
      } else {
        const body: RecordCreate = {
          type: this.type,
          title: this.title.trim().length > 0 ? this.title.trim() : null,
          content: this.content.trim().length > 0 ? this.content.trim() : null,
          mood: this.mood.length > 0 ? this.mood : null,
          tags: this.tags.trim().length > 0 ? this.tags.trim() : null,
          book_title: this.bookTitle.trim().length > 0 ? this.bookTitle.trim() : null,
          book_author: this.bookAuthor.trim().length > 0 ? this.bookAuthor.trim() : null,
          project: this.project.trim().length > 0 ? this.project.trim() : null,
          record_date: this.recordDate,
          record_time: this.recordTime.length > 0 ? this.recordTime : null,
        };
        await Api.createRecord(body);
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
        title: '移入回收站',
        message: '记录将移入回收站，保留期内可恢复。',
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '移入', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.deleteRecord(this.recordId);
        toast('已移入回收站');
        router.back();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: this.recordId > 0 ? '编辑记录' : '新建记录',
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
              this.typeSection();
            },
          });
          Card({
            content: () => {
              this.bodySection();
            },
          });
          Card({
            content: () => {
              this.metaSection();
            },
          });
          if (this.recordId > 0) {
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
      .fontColor(Theme.OK)
      .fontWeight(FontWeight.Medium)
      .onClick(() => {
        if (!this.saving) {
          this.save();
        }
      });
  }

  @Builder
  typeSection() {
    Column({ space: 10 }) {
      SegmentPicker({
        labels: ['日记', '工作日志', '读书笔记', '随手记'],
        values: Options.RECORD_TYPES,
        selected: this.type,
        onSelect: (v: string) => {
          this.type = v;
        },
      });
      if (this.templates.length > 0 && this.recordId === 0) {
        Text('模板').fontSize(11).fontColor(Theme.TEXT_WEAK);
        Flex({ wrap: FlexWrap.Wrap }) {
          ForEach(this.templatesOfType(), (t: TemplateOut) => {
            Text(`${t.icon} ${t.name}`)
              .fontSize(12)
              .fontColor(Theme.BRAND_DARK)
              .backgroundColor('#EEF2FF')
              .borderRadius(8)
              .padding({ left: 9, right: 9, top: 5, bottom: 5 })
              .margin({ right: 7, bottom: 7 })
              .onClick(() => {
                this.applyTemplate(t);
              });
          }, (t: TemplateOut) => `${t.id}`);
        }
        .width('100%');
      }
    }
    .width('100%');
  }

  /** 只展示当前类型的模板，减少无关选项。 */
  private templatesOfType(): TemplateOut[] {
    return this.templates.filter((t: TemplateOut) => t.type === this.type);
  }

  @Builder
  bodySection() {
    Column({ space: 10 }) {
      TextInput({ placeholder: '标题（留空自动用日期）', text: this.title })
        .height(44)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.title = v;
        });
      TextArea({ placeholder: '写下今天…', text: this.content })
        .height(180)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.content = v;
        });
      Row({ space: 6 }) {
        Text('心情').fontSize(12).fontColor(Theme.TEXT_SUB);
        ForEach(MOODS, (m: string) => {
          Text(m)
            .fontSize(19)
            .opacity(this.mood === m ? 1 : 0.4)
            .onClick(() => {
              this.mood = this.mood === m ? '' : m;
            });
        }, (m: string) => m);
      }
      .width('100%');
    }
    .width('100%');
  }

  @Builder
  metaSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '归档信息' });
      Row({ space: 8 }) {
        Text(this.recordDate)
          .fontSize(13)
          .fontColor(Theme.TEXT)
          .backgroundColor('#F1F3F5')
          .borderRadius(9)
          .padding({ left: 12, right: 12, top: 8, bottom: 8 })
          .onClick(() => {
            this.pickDate();
          });
        Text(this.recordTime.length > 0 ? this.recordTime : '时间（可选）')
          .fontSize(13)
          .fontColor(this.recordTime.length > 0 ? Theme.TEXT : Theme.TEXT_SUB)
          .backgroundColor('#F1F3F5')
          .borderRadius(9)
          .padding({ left: 12, right: 12, top: 8, bottom: 8 })
          .onClick(() => {
            this.pickTime();
          });
      }
      .width('100%');

      if (this.type === 'reading') {
        TextInput({ placeholder: '书名', text: this.bookTitle })
          .height(42)
          .borderRadius(10)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.bookTitle = v;
          });
        TextInput({ placeholder: '作者', text: this.bookAuthor })
          .height(42)
          .borderRadius(10)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.bookAuthor = v;
          });
      }
      if (this.type === 'worklog') {
        TextInput({ placeholder: '项目 / 模块', text: this.project })
          .height(42)
          .borderRadius(10)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.project = v;
          });
      }
      TextInput({ placeholder: '标签，逗号分隔（可选）', text: this.tags })
        .height(42)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.tags = v;
        });
    }
    .width('100%');
  }
}
