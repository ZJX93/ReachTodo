/**
 * 标签管理。
 *
 * 标签是「轻量分类」——比维度更随意，所以这里允许随手新建、改色、删除。
 * 删除标签只拆掉「任务 ↔ 标签」的关联，不碰任务本身：标签归零不该连带删除内容。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { TagOut } from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { Card, NavBar, StateHint } from '../view/Common';

const PALETTE: string[] = [
  '#3B82F6', '#8B5CF6', '#EC4899', '#EF4444', '#F59E0B',
  '#10B981', '#14B8A6', '#06B6D4', '#6366F1', '#64748B',
];

@Entry
@Component
struct TagsPage {
  @State private tags: TagOut[] = [];
  @State private loading: boolean = true;
  @State private error: string = '';
  @State private saving: boolean = false;

  @State private newName: string = '';
  @State private newColor: string = PALETTE[0];

  @State private editId: number = 0;
  @State private editName: string = '';
  @State private editColor: string = PALETTE[0];

  aboutToAppear(): void {
    this.load();
  }

  onPageShow(): void {
    if (!this.loading) {
      this.load();
    }
  }

  private async load(): Promise<void> {
    this.loading = this.tags.length === 0;
    this.error = '';
    try {
      this.tags = await AppStore.loadTags(true);
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  private async addTag(): Promise<void> {
    const name: string = this.newName.trim();
    if (name.length === 0) {
      toast('请输入标签名');
      return;
    }
    this.saving = true;
    try {
      await Api.createTag({ name: name, color: this.newColor });
      this.newName = '';
      await this.load();
    } catch (err) {
      toastError(err as object);
    } finally {
      this.saving = false;
    }
  }

  private startEdit(t: TagOut): void {
    this.editId = t.id;
    this.editName = t.name;
    this.editColor = t.color;
  }

  private async saveEdit(): Promise<void> {
    const name: string = this.editName.trim();
    if (name.length === 0) {
      toast('标签名不能为空');
      return;
    }
    this.saving = true;
    try {
      await Api.updateTag(this.editId, { name: name, color: this.editColor });
      this.editId = 0;
      await this.load();
    } catch (err) {
      toastError(err as object);
    } finally {
      this.saving = false;
    }
  }

  private async remove(t: TagOut): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '删除标签',
        message: `删除「${t.name}」只会移除标签关联，不影响任务本身。`,
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '删除', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.deleteTag(t.id);
        await this.load();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: '标签管理',
        subtitle: `${this.tags.length} 个标签`,
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
                this.addSection();
              },
            });
            ForEach(this.tags, (t: TagOut) => {
              Card({
                content: () => {
                  if (this.editId === t.id) {
                    this.editRow(t);
                  } else {
                    this.tagRow(t);
                  }
                },
              });
            }, (t: TagOut) => `${t.id}`);
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
  addSection() {
    Column({ space: 10 }) {
      Text('新建标签').fontSize(15).fontWeight(FontWeight.Medium).fontColor(Theme.TEXT);
      Row({ space: 8 }) {
        Row().width(16).height(16).backgroundColor(this.newColor).borderRadius(8);
        TextInput({ placeholder: '标签名', text: this.newName })
          .height(38)
          .layoutWeight(1)
          .borderRadius(9)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.newName = v;
          })
          .onSubmit(() => {
            this.addTag();
          });
        Button('添加')
          .fontSize(13)
          .height(34)
          .backgroundColor('#EEF2FF')
          .fontColor(Theme.BRAND_DARK)
          .onClick(() => {
            this.addTag();
          });
      }
      .width('100%');
      this.palette(this.newColor, (c: string) => {
        this.newColor = c;
      });
    }
    .width('100%');
  }

  @Builder
  palette(selected: string, onPick: (c: string) => void) {
    Flex({ wrap: FlexWrap.Wrap }) {
      ForEach(PALETTE, (c: string) => {
        Row()
          .width(26)
          .height(26)
          .backgroundColor(c)
          .borderRadius(13)
          .border({ width: selected === c ? 2 : 0, color: Theme.TEXT })
          .margin({ right: 8, bottom: 8 })
          .onClick(() => {
            onPick(c);
          });
      }, (c: string) => c);
    }
    .width('100%');
  }

  @Builder
  tagRow(t: TagOut) {
    Row({ space: 10 }) {
      Row().width(14).height(14).backgroundColor(t.color).borderRadius(7);
      Text(t.name).fontSize(15).fontColor(Theme.TEXT).layoutWeight(1);
      Text(`${t.task_count}`).fontSize(12).fontColor(Theme.TEXT_WEAK);
      Text('编辑')
        .fontSize(13)
        .fontColor(Theme.BRAND)
        .onClick(() => {
          this.startEdit(t);
        });
      Text('删除')
        .fontSize(13)
        .fontColor(Theme.DANGER)
        .onClick(() => {
          this.remove(t);
        });
    }
    .width('100%')
    .padding({ top: 4, bottom: 4 });
  }

  @Builder
  editRow(t: TagOut) {
    Column({ space: 10 }) {
      Row({ space: 8 }) {
        Row().width(16).height(16).backgroundColor(this.editColor).borderRadius(8);
        TextInput({ placeholder: '标签名', text: this.editName })
          .height(38)
          .layoutWeight(1)
          .borderRadius(9)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.editName = v;
          });
      }
      .width('100%');
      this.palette(this.editColor, (c: string) => {
        this.editColor = c;
      });
      Row({ space: 10 }) {
        Button('取消')
          .layoutWeight(1)
          .height(36)
          .backgroundColor('#F1F3F5')
          .fontColor(Theme.TEXT)
          .onClick(() => {
            this.editId = 0;
          });
        Button('保存')
          .layoutWeight(1)
          .height(36)
          .backgroundColor(Theme.BRAND)
          .fontColor('#FFFFFF')
          .onClick(() => {
            this.saveEdit();
          });
      }
      .width('100%');
    }
    .width('100%');
  }
}
