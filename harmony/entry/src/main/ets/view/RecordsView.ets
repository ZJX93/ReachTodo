/**
 * 记录页：日记 / 工作日志 / 读书笔记 / 随手记。
 *
 * 与「任务」的分工：任务是未来要做的，记录是已经发生的。两者共用日历，
 * 但不混在一个列表里——把它们混排会让「今天还剩什么没做」变得模糊。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import { RecordOut, RecordQuery } from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { EmptyTip, SegmentPicker, StateHint } from './Common';

@Component
export struct RecordsView {
  @Link @Watch('onRefreshKeyChange') refreshKey: number;

  @State private loading: boolean = true;
  @State private error: string = '';
  @State private records: RecordOut[] = [];
  @State private type: string = 'all';
  @State private keyword: string = '';

  private searchTimer: number = -1;

  aboutToAppear(): void {
    this.load();
  }

  onRefreshKeyChange(): void {
    this.load();
  }

  private async load(): Promise<void> {
    this.loading = this.records.length === 0;
    this.error = '';
    const q: RecordQuery = { limit: 200 };
    if (this.type !== 'all') {
      q.type = this.type;
    }
    if (this.keyword.trim().length > 0) {
      q.q = this.keyword.trim();
    }
    try {
      this.records = await Api.records(q);
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

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

  private async remove(r: RecordOut): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '移入回收站',
        message: `「${r.title}」将移入回收站。`,
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '移入', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        await Api.deleteRecord(r.id);
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
        Column({ space: 10 }) {
          TextInput({ placeholder: '搜索标题、正文、书名', text: this.keyword })
            .height(38)
            .borderRadius(10)
            .backgroundColor('#F1F3F5')
            .onChange((v: string) => {
              this.onKeywordChange(v);
            });
          SegmentPicker({
            labels: ['全部', '日记', '日志', '读书', '随手'],
            values: ['all', 'diary', 'worklog', 'reading', 'note'],
            selected: this.type,
            onSelect: (v: string) => {
              this.type = v;
              this.load();
            },
          });
        }
        .width('100%')
        .padding({ left: 14, right: 14, top: 10, bottom: 10 })
        .backgroundColor(Theme.CARD)
        .border({ width: { bottom: 1 }, color: Theme.BORDER });

        if (this.loading || this.error.length > 0) {
          StateHint({
            loading: this.loading,
            error: this.error,
            onRetry: () => {
              this.load();
            },
          });
        } else if (this.records.length === 0) {
          EmptyTip({ text: '还没有记录', hint: '点右下角「＋」写下今天的第一条' });
        } else {
          List({ space: 10 }) {
            ForEach(this.records, (r: RecordOut) => {
              ListItem() {
                this.recordCard(r);
              }
            }, (r: RecordOut) => `${r.id}-${r.updated_at ?? ''}`);
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
        .backgroundColor(Theme.OK)
        .margin({ right: 18, bottom: 20 })
        .onClick(() => {
          router.pushUrl({ url: 'pages/RecordEditPage' });
        });
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  recordCard(r: RecordOut) {
    Column({ space: 6 }) {
      Row({ space: 8 }) {
        Text(Theme.recordTypeLabel(r.type))
          .fontSize(11)
          .fontColor(Theme.BRAND)
          .backgroundColor('#EEF2FF')
          .borderRadius(6)
          .padding({ left: 6, right: 6, top: 2, bottom: 2 });
        Text(r.title)
          .fontSize(15)
          .fontColor(Theme.TEXT)
          .layoutWeight(1)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis });
        if (r.mood && r.mood.length > 0) {
          Text(r.mood).fontSize(14);
        }
      }
      .width('100%');

      if (r.content && r.content.length > 0) {
        Text(r.content)
          .fontSize(13)
          .fontColor(Theme.TEXT_SUB)
          .maxLines(3)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%');
      }

      Row({ space: 10 }) {
        Text(`${r.record_date}${r.record_time ? ' ' + r.record_time : ''}`)
          .fontSize(11)
          .fontColor(Theme.TEXT_WEAK);
        if (r.book_title && r.book_title.length > 0) {
          Text(`《${r.book_title}》`).fontSize(11).fontColor(Theme.PURPLE);
        }
        if (r.project && r.project.length > 0) {
          Text(r.project).fontSize(11).fontColor(Theme.TEXT_WEAK);
        }
        if (r.tags && r.tags.length > 0) {
          Text('#' + r.tags.join(' #')).fontSize(11).fontColor(Theme.BRAND);
        }
      }
      .width('100%');
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
    .padding(13)
    .backgroundColor(Theme.CARD)
    .borderRadius(Theme.RADIUS)
    .onClick(() => {
      router.pushUrl({ url: 'pages/RecordEditPage', params: { recordId: r.id } });
    })
    .gesture(
      LongPressGesture().onAction(() => {
        this.remove(r);
      })
    );
  }
}
