/**
 * 回收站。
 *
 * 软删除的产物：任务 / 记录被删除后保留 `retention_days` 天，期间可恢复。
 * 这里只做三件事——恢复、彻底删除、清空，不做任何业务编辑，
 * 因为「在回收站里修改」是反直觉的，用户要改就先恢复出去改。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { TrashItem, TrashList } from '../common/Models';
import { DateUtil } from '../common/DateUtil';
import { Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { EmptyTip, NavBar, StateHint } from '../view/Common';

@Entry
@Component
struct TrashPage {
  @State private list: TrashList | null = null;
  @State private loading: boolean = true;
  @State private error: string = '';

  aboutToAppear(): void {
    this.load();
  }

  onPageShow(): void {
    if (!this.loading) {
      this.load();
    }
  }

  private async load(): Promise<void> {
    this.loading = this.list === null;
    this.error = '';
    try {
      this.list = await Api.trash();
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  private kindIcon(kind: string): string {
    return kind === 'record' ? '✎' : '☰';
  }

  private async restore(item: TrashItem): Promise<void> {
    try {
      await Api.restoreTrash(item.kind, item.id);
      toast('已恢复');
      await this.load();
    } catch (err) {
      toastError(err as object);
    }
  }

  private async purge(item: TrashItem): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '彻底删除',
        message: `"${item.title}" 将被永久删除且无法恢复。`,
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '删除', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.purgeTrash(item.kind, item.id);
        toast('已彻底删除');
        await this.load();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  private async emptyAll(): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '清空回收站',
        message: '所有回收站内容将永久删除，无法恢复。',
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '清空', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.emptyTrash();
        toast('已清空');
        await this.load();
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: '回收站',
        subtitle: this.list ? `保留 ${this.list.retention_days} 天` : '',
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
      } else if ((this.list?.items.length ?? 0) === 0) {
        EmptyTip({ text: '回收站是空的', hint: '删除的任务和记录会先到这里' });
      } else {
        Column({ space: 0 }) {
          Scroll() {
            Column({ space: Theme.GAP }) {
              ForEach(this.list!.items, (item: TrashItem) => {
                this.itemCard(item);
              }, (item: TrashItem) => `${item.kind}-${item.id}`);
              Row().height(16);
            }
            .width('100%')
            .padding({ left: Theme.PAGE_PADDING, right: Theme.PAGE_PADDING, top: 12 });
          }
          .layoutWeight(1)
          .scrollBar(BarState.Off);

          Button('清空回收站')
            .width('100%')
            .height(44)
            .margin({ left: 16, right: 16, bottom: 16 })
            .borderRadius(12)
            .backgroundColor('#FEE2E2')
            .fontColor(Theme.DANGER)
            .onClick(() => {
              this.emptyAll();
            });
        }
        .layoutWeight(1)
        .width('100%');
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  itemCard(item: TrashItem) {
    Row({ space: 10 }) {
      Text(this.kindIcon(item.kind))
        .fontSize(18)
        .fontColor(Theme.TEXT_WEAK)
        .width(24)
        .textAlign(TextAlign.Center);
      Column({ space: 3 }) {
        Text(item.title)
          .fontSize(15)
          .fontColor(Theme.TEXT)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%');
        if (item.subtitle && item.subtitle.length > 0) {
          Text(item.subtitle)
            .fontSize(12)
            .fontColor(Theme.TEXT_SUB)
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
            .width('100%');
        }
        if (item.deleted_at && item.deleted_at.length > 0) {
          Text(`删除于 ${DateUtil.fmtDateTime(item.deleted_at)}`)
            .fontSize(11)
            .fontColor(Theme.TEXT_WEAK);
        }
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1);

      Text('恢复')
        .fontSize(13)
        .fontColor(Theme.OK)
        .onClick(() => {
          this.restore(item);
        });
      Text('删除')
        .fontSize(13)
        .fontColor(Theme.DANGER)
        .onClick(() => {
          this.purge(item);
        });
    }
    .width('100%')
    .padding(14)
    .backgroundColor(Theme.CARD)
    .borderRadius(Theme.RADIUS);
  }
}
