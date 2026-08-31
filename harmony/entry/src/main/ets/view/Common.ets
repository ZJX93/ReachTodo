/**
 * 通用 UI 片段。
 *
 * 抽出来的标准：**在 3 个以上页面出现、且视觉必须一致**。
 * 只用一两次的布局直接写在页面里，过度抽象反而让页面难读。
 */
import { Theme } from '../common/Theme';

/** 顶部标题栏（带返回箭头的二级页面用）。 */
@Component
export struct NavBar {
  title: string = '';
  subtitle: string = '';
  onBack?: () => void;
  @BuilderParam trailing?: () => void;

  build() {
    Row({ space: 8 }) {
      if (this.onBack) {
        Text('‹')
          .fontSize(30)
          .fontColor(Theme.TEXT)
          .width(32)
          .textAlign(TextAlign.Center)
          .onClick(() => {
            this.onBack?.();
          });
      }
      Column({ space: 2 }) {
        Text(this.title).fontSize(19).fontWeight(FontWeight.Bold).fontColor(Theme.TEXT);
        if (this.subtitle.length > 0) {
          Text(this.subtitle).fontSize(12).fontColor(Theme.TEXT_SUB);
        }
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1);

      if (this.trailing) {
        this.trailing();
      }
    }
    .width('100%')
    .padding({ left: 12, right: 16, top: 10, bottom: 10 })
    .backgroundColor(Theme.CARD)
    .border({ width: { bottom: 1 }, color: Theme.BORDER });
  }
}

/** 卡片容器：统一圆角、留白与底色。 */
@Component
export struct Card {
  @BuilderParam content: () => void;
  padding: number = 14;

  build() {
    Column() {
      this.content();
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
    .padding(this.padding)
    .backgroundColor(Theme.CARD)
    .borderRadius(Theme.RADIUS);
  }
}

/** 分区小标题。 */
@Component
export struct SectionTitle {
  title: string = '';
  action: string = '';
  onAction?: () => void;

  build() {
    Row() {
      Text(this.title)
        .fontSize(15)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.TEXT)
        .layoutWeight(1);
      if (this.action.length > 0) {
        Text(this.action)
          .fontSize(13)
          .fontColor(Theme.BRAND)
          .onClick(() => {
            this.onAction?.();
          });
      }
    }
    .width('100%')
    .padding({ top: 4, bottom: 6 });
  }
}

/** 空状态。文案要具体到「下一步该做什么」，而不是干巴巴的「暂无数据」。 */
@Component
export struct EmptyTip {
  text: string = '暂无内容';
  hint: string = '';

  build() {
    Column({ space: 6 }) {
      Text(this.text).fontSize(14).fontColor(Theme.TEXT_SUB);
      if (this.hint.length > 0) {
        Text(this.hint).fontSize(12).fontColor(Theme.TEXT_WEAK).textAlign(TextAlign.Center);
      }
    }
    .width('100%')
    .padding({ top: 32, bottom: 32 })
    .justifyContent(FlexAlign.Center);
  }
}

/** 加载中 / 加载失败的统一占位。 */
@Component
export struct StateHint {
  loading: boolean = false;
  error: string = '';
  onRetry?: () => void;

  build() {
    Column({ space: 10 }) {
      if (this.loading) {
        LoadingProgress().width(36).height(36).color(Theme.BRAND);
        Text('加载中…').fontSize(13).fontColor(Theme.TEXT_SUB);
      } else if (this.error.length > 0) {
        Text(this.error).fontSize(13).fontColor(Theme.DANGER).textAlign(TextAlign.Center);
        if (this.onRetry) {
          Button('重试')
            .fontSize(13)
            .backgroundColor(Theme.BRAND)
            .height(32)
            .onClick(() => {
              this.onRetry?.();
            });
        }
      }
    }
    .width('100%')
    .padding({ top: 28, bottom: 28 })
    .justifyContent(FlexAlign.Center);
  }
}

/** 标签 / 属性小胶囊。 */
@Component
export struct Chip {
  text: string = '';
  color: string = Theme.BRAND;
  filled: boolean = false;

  build() {
    Text(this.text)
      .fontSize(11)
      .fontColor(this.filled ? '#FFFFFF' : this.color)
      .backgroundColor(this.filled ? this.color : '#00000000')
      .border({ width: this.filled ? 0 : 1, color: this.color })
      .borderRadius(9)
      .padding({ left: 7, right: 7, top: 2, bottom: 2 });
  }
}

/** 横向单选组（紧急度 / 重要度 / 排序等）。 */
@Component
export struct SegmentPicker {
  labels: string[] = [];
  values: string[] = [];
  @Prop selected: string;
  onSelect: (value: string) => void = () => {
  };

  build() {
    Row({ space: 6 }) {
      ForEach(this.values, (v: string, idx: number) => {
        Text(this.labels[idx] ?? v)
          .fontSize(13)
          .fontColor(this.selected === v ? '#FFFFFF' : Theme.TEXT_SUB)
          .backgroundColor(this.selected === v ? Theme.BRAND : '#F1F3F5')
          .borderRadius(8)
          .padding({ left: 12, right: 12, top: 6, bottom: 6 })
          .onClick(() => {
            this.onSelect(v);
          });
      }, (v: string) => v);
    }
    .width('100%');
  }
}

/** 设置项行：左标题右内容，可点。 */
@Component
export struct SettingRow {
  label: string = '';
  value: string = '';
  showArrow: boolean = true;
  onTap?: () => void;

  build() {
    Row({ space: 8 }) {
      Text(this.label).fontSize(15).fontColor(Theme.TEXT).layoutWeight(1);
      Text(this.value)
        .fontSize(13)
        .fontColor(Theme.TEXT_SUB)
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .constraintSize({ maxWidth: '55%' });
      if (this.showArrow) {
        Text('›').fontSize(20).fontColor(Theme.TEXT_WEAK);
      }
    }
    .width('100%')
    .padding({ top: 13, bottom: 13 })
    .onClick(() => {
      this.onTap?.();
    });
  }
}

/** 进度条（目标进度 / 维度占比）。 */
@Component
export struct ProgressBar {
  percent: number = 0;
  color: string = Theme.BRAND;

  build() {
    Stack({ alignContent: Alignment.Start }) {
      Row().width('100%').height(6).backgroundColor('#EEF0F3').borderRadius(3);
      Row()
        .width(`${Math.max(0, Math.min(100, this.percent))}%`)
        .height(6)
        .backgroundColor(this.color)
        .borderRadius(3);
    }
    .width('100%')
    .height(6);
  }
}
