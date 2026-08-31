/**
 * 日历页：公历 + 农历 + 节气 + 法定节假日 + 当日任务/记录数量。
 *
 * 农历用**离线算法**渲染（`Lunar.ets`）：42 个格子若各发一次接口就是 42 次请求，
 * 且离线不可用。节假日（调休/补班）无法离线推算，按年拉一次并缓存在内存里。
 */
import router from '@ohos.router';
import { Api } from '../common/Api';
import { DateUtil } from '../common/DateUtil';
import { computeLunar, lunarLabel } from '../common/Lunar';
import { CalendarDay, HolidayInfo } from '../common/Models';
import { Theme } from '../common/Theme';
import { errorText } from '../common/Toast';
import { AppStore } from '../stores/AppStore';

interface DayCell {
  date: string;
  day: number;
  inMonth: boolean;
  isToday: boolean;
  lunar: string;
  holiday: string;
  isOffDay: boolean;
  records: number;
  tasks: number;
}

@Component
export struct CalendarView {
  @Link @Watch('onRefreshKeyChange') refreshKey: number;

  @State private year: number = 0;
  @State private month: number = 0;
  @State private cells: DayCell[] = [];
  @State private loading: boolean = true;
  @State private error: string = '';
  @State private selected: string = '';

  /** 按年缓存节假日，避免来回翻月反复请求。 */
  private holidayCache: Map<number, Record<string, HolidayInfo>> = new Map();

  aboutToAppear(): void {
    const today: string = DateUtil.today();
    this.year = DateUtil.yearOf(today);
    this.month = DateUtil.monthOf(today);
    this.selected = today;
    this.load();
  }

  onRefreshKeyChange(): void {
    this.load();
  }

  private async holidaysOf(year: number): Promise<Record<string, HolidayInfo>> {
    const cached = this.holidayCache.get(year);
    if (cached !== undefined) {
      return cached;
    }
    try {
      const res: Record<string, HolidayInfo> = await Api.holidays(year);
      this.holidayCache.set(year, res);
      return res;
    } catch (e) {
      // 节假日接口失败不该让整个日历不可用，用空表兜底
      const empty: Record<string, HolidayInfo> = {};
      this.holidayCache.set(year, empty);
      return empty;
    }
  }

  private async load(): Promise<void> {
    this.loading = this.cells.length === 0;
    this.error = '';
    const weekStart: string = AppStore.settings().weekStart;
    const grid: string[] = DateUtil.monthGrid(this.year, this.month, weekStart);
    const today: string = DateUtil.today();

    try {
      const holidays: Record<string, HolidayInfo> = await this.holidaysOf(this.year);
      let counts: CalendarDay[] = [];
      try {
        counts = await Api.recordsCalendar(this.year, this.month);
      } catch (e) {
        // 数量是增强信息，失败时格子照常显示
      }
      const countMap: Map<string, CalendarDay> = new Map();
      for (const c of counts) {
        countMap.set(c.date, c);
      }

      const next: DayCell[] = [];
      for (const ds of grid) {
        const info = computeLunar(ds);
        const hol: HolidayInfo | undefined = holidays[ds];
        const cnt: CalendarDay | undefined = countMap.get(ds);
        next.push({
          date: ds,
          day: DateUtil.dayOf(ds),
          inMonth: DateUtil.monthOf(ds) === this.month,
          isToday: ds === today,
          lunar: lunarLabel(info),
          holiday: hol?.name ?? '',
          isOffDay: hol?.isOffDay ?? false,
          records: cnt?.total ?? 0,
          tasks: cnt?.tasks ?? 0,
        });
      }
      this.cells = next;
    } catch (err) {
      this.error = errorText(err as object);
    } finally {
      this.loading = false;
    }
  }

  private shiftMonth(delta: number): void {
    let m: number = this.month + delta;
    let y: number = this.year;
    if (m < 1) {
      m = 12;
      y--;
    } else if (m > 12) {
      m = 1;
      y++;
    }
    this.year = y;
    this.month = m;
    this.load();
  }

  private jumpToday(): void {
    const today: string = DateUtil.today();
    this.year = DateUtil.yearOf(today);
    this.month = DateUtil.monthOf(today);
    this.selected = today;
    this.load();
  }

  build() {
    Column({ space: 0 }) {
      this.header();
      this.weekHeader();
      if (this.loading) {
        Column() {
          LoadingProgress().width(34).height(34).color(Theme.BRAND);
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center);
      } else if (this.error.length > 0) {
        Column({ space: 10 }) {
          Text(this.error).fontSize(13).fontColor(Theme.DANGER).textAlign(TextAlign.Center);
          Button('重试').fontSize(13).height(32).onClick(() => {
            this.load();
          });
        }
        .width('100%')
        .layoutWeight(1)
        .padding(20)
        .justifyContent(FlexAlign.Center);
      } else {
        this.grid();
        this.footer();
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }

  @Builder
  header() {
    Row({ space: 12 }) {
      Text('‹')
        .fontSize(26)
        .fontColor(Theme.TEXT)
        .width(30)
        .textAlign(TextAlign.Center)
        .onClick(() => {
          this.shiftMonth(-1);
        });
      Column({ space: 2 }) {
        Text(`${this.year}年${this.month}月`)
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.TEXT);
        Text(this.monthLunarHint()).fontSize(11).fontColor(Theme.TEXT_SUB);
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Center);
      Text('›')
        .fontSize(26)
        .fontColor(Theme.TEXT)
        .width(30)
        .textAlign(TextAlign.Center)
        .onClick(() => {
          this.shiftMonth(1);
        });
      Text('今天')
        .fontSize(13)
        .fontColor(Theme.BRAND)
        .onClick(() => {
          this.jumpToday();
        });
    }
    .width('100%')
    .padding({ left: 10, right: 14, top: 10, bottom: 10 })
    .backgroundColor(Theme.CARD);
  }

  /** 顶部副标题：本月首日的农历年月，帮助建立公历-农历的对应感。 */
  private monthLunarHint(): string {
    const first: string = `${this.year}-${this.month < 10 ? '0' : ''}${this.month}-01`;
    const info = computeLunar(first);
    return `${info.nnian ?? ''}年 · ${info.YEARGANZHI ?? ''}${info.shengxiao ?? ''}年`;
  }

  @Builder
  weekHeader() {
    Row() {
      ForEach(DateUtil.weekLabels(AppStore.settings().weekStart), (w: string) => {
        Text(w)
          .fontSize(12)
          .fontColor(w === '六' || w === '日' ? Theme.DANGER : Theme.TEXT_SUB)
          .layoutWeight(1)
          .textAlign(TextAlign.Center);
      }, (w: string) => w);
    }
    .width('100%')
    .padding({ top: 6, bottom: 6 })
    .backgroundColor(Theme.CARD)
    .border({ width: { bottom: 1 }, color: Theme.BORDER });
  }

  @Builder
  grid() {
    Grid() {
      ForEach(this.cells, (c: DayCell) => {
        GridItem() {
          this.cell(c);
        }
      }, (c: DayCell) => c.date);
    }
    .columnsTemplate('1fr 1fr 1fr 1fr 1fr 1fr 1fr')
    .rowsTemplate('1fr 1fr 1fr 1fr 1fr 1fr')
    .width('100%')
    .layoutWeight(1)
    .backgroundColor(Theme.CARD);
  }

  @Builder
  cell(c: DayCell) {
    Column({ space: 1 }) {
      Text(`${c.day}`)
        .fontSize(16)
        .fontWeight(c.isToday ? FontWeight.Bold : FontWeight.Normal)
        .fontColor(this.dayColor(c));
      Text(c.holiday.length > 0 ? c.holiday : c.lunar)
        .fontSize(9)
        .fontColor(c.holiday.length > 0
          ? (c.isOffDay ? Theme.DANGER : Theme.OK)
          : (c.inMonth ? Theme.TEXT_SUB : Theme.TEXT_WEAK))
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .width('100%')
        .textAlign(TextAlign.Center);
      Row({ space: 2 }) {
        if (c.tasks > 0) {
          Circle().width(4).height(4).fill(Theme.BRAND);
        }
        if (c.records > 0) {
          Circle().width(4).height(4).fill(Theme.OK);
        }
      }
      .height(6);
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .backgroundColor(this.selected === c.date ? '#EEF2FF' : '#00000000')
    .borderRadius(8)
    .onClick(() => {
      this.selected = c.date;
      router.pushUrl({ url: 'pages/DayDetailPage', params: { date: c.date } });
    });
  }

  private dayColor(c: DayCell): string {
    if (!c.inMonth) {
      return Theme.TEXT_WEAK;
    }
    if (c.isToday) {
      return Theme.BRAND;
    }
    if (c.isOffDay) {
      return Theme.DANGER;
    }
    return Theme.TEXT;
  }

  @Builder
  footer() {
    Row({ space: 14 }) {
      Row({ space: 4 }) {
        Circle().width(5).height(5).fill(Theme.BRAND);
        Text('有任务').fontSize(11).fontColor(Theme.TEXT_SUB);
      }
      Row({ space: 4 }) {
        Circle().width(5).height(5).fill(Theme.OK);
        Text('有记录').fontSize(11).fontColor(Theme.TEXT_SUB);
      }
      Blank();
      Text('点击日期查看黄历与当日安排').fontSize(11).fontColor(Theme.TEXT_WEAK);
    }
    .width('100%')
    .padding({ left: 14, right: 14, top: 8, bottom: 10 })
    .backgroundColor(Theme.CARD);
  }
}
