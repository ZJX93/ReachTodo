/**
 * 偏好设置（云端同步）。
 *
 * 所有偏好都存在服务端 `/api/settings`，本地只留快照。
 * 这样换设备、装鸿蒙 + 安卓双端时不需要重新配一遍；
 * 「本地设置」在多端场景下必然导致两边行为不一致。
 */
import promptAction from '@ohos.promptAction';
import router from '@ohos.router';
import { Api } from '../common/Api';
import { AppSettings, SettingsOut } from '../common/Models';
import { Prefs } from '../common/Prefs';
import { Options, Theme } from '../common/Theme';
import { errorText, toast, toastError } from '../common/Toast';
import { AppStore } from '../stores/AppStore';
import { Card, NavBar, SectionTitle, SegmentPicker, SettingRow } from '../view/Common';

@Entry
@Component
struct SettingsPage {
  @State private s: AppSettings = Prefs.settings();
  @State private serverUrl: string = '';
  @State private loading: boolean = true;
  @State private saving: boolean = false;
  @State private dirty: boolean = false;

  aboutToAppear(): void {
    this.serverUrl = Prefs.serverUrl();
    this.load();
  }

  private async load(): Promise<void> {
    try {
      this.s = await AppStore.loadSettings();
    } catch (err) {
      // 离线时用本地快照继续，让用户至少能看到当前配置
      this.s = Prefs.settings();
      toast('未能从服务器读取偏好，当前显示本地快照');
    } finally {
      this.loading = false;
    }
  }

  /**
   * 逐字段更新。
   * ArkTS 没有对象展开语法，且 `@State` 需要整体赋值才会触发刷新，
   * 因此这里显式复制一份再改字段。
   */
  private patch(mutator: (draft: AppSettings) => void): void {
    const draft: AppSettings = Prefs.mergeSettings(this.s, this.s);
    mutator(draft);
    this.s = draft;
    this.dirty = true;
  }

  private async save(): Promise<void> {
    this.saving = true;
    try {
      this.s = await AppStore.saveAllSettings(this.s);
      this.dirty = false;
      // 提醒相关偏好（开关 / 默认提前量）改动后必须重排，否则要等下次进前台
      AppStore.syncReminders().catch(() => {
      });
      toast('已保存并同步');
    } catch (err) {
      toastError(err as object);
    } finally {
      this.saving = false;
    }
  }

  private applyServerUrl(): void {
    Prefs.setServerUrl(this.serverUrl);
    toast('服务器地址已更新');
  }

  private async resetFeedToken(): Promise<void> {
    try {
      const res: promptAction.ShowDialogSuccessResponse = await promptAction.showDialog({
        title: '重置订阅令牌',
        message: '重置后旧的日历订阅地址立即失效，需要在日历应用中重新添加。',
        buttons: [{ text: '取消', color: Theme.TEXT_SUB }, { text: '重置', color: Theme.DANGER }],
      });
      if (res.index === 1) {
        const out: SettingsOut = await Api.resetFeedToken();
        Prefs.setFeedPath(out.feed_path ?? '');
        toast('已重置');
      }
    } catch (err) {
      toastError(err as object);
    }
  }

  private async changePassword(): Promise<void> {
    toast('请在网页端修改密码');
  }

  build() {
    Column({ space: 0 }) {
      NavBar({
        title: '偏好设置',
        subtitle: this.dirty ? '有未保存的修改' : '与服务器同步',
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
              this.serverSection();
            },
          });
          Card({
            content: () => {
              this.viewSection();
            },
          });
          Card({
            content: () => {
              this.reminderSection();
            },
          });
          Card({
            content: () => {
              this.focusSection();
            },
          });
          Card({
            content: () => {
              this.lunarSection();
            },
          });
          Card({
            content: () => {
              this.accountSection();
            },
          });
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
      .fontColor(this.dirty ? Theme.BRAND : Theme.TEXT_WEAK)
      .fontWeight(FontWeight.Medium)
      .onClick(() => {
        if (!this.saving) {
          this.save();
        }
      });
  }

  @Builder
  serverSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '服务器' });
      TextInput({ placeholder: 'https://reach.example.com', text: this.serverUrl })
        .height(42)
        .borderRadius(10)
        .backgroundColor('#F5F6F8')
        .onChange((v: string) => {
          this.serverUrl = v;
        });
      Row({ space: 10 }) {
        Button('应用')
          .fontSize(13)
          .height(32)
          .backgroundColor('#EEF2FF')
          .fontColor(Theme.BRAND_DARK)
          .onClick(() => {
            this.applyServerUrl();
          });
        Button('测试连接')
          .fontSize(13)
          .height(32)
          .backgroundColor('#F1F3F5')
          .fontColor(Theme.TEXT)
          .onClick(() => {
            Api.health()
              .then(() => {
                toast('连接正常');
              })
              .catch((e: object) => {
                toast(errorText(e));
              });
          });
      }
      .width('100%');
      Text('修改地址不会清除登录状态；若换了服务器实例，请退出登录后重新登录')
        .fontSize(11)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%');
  }

  @Builder
  viewSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '显示' });
      Text('默认视图').fontSize(12).fontColor(Theme.TEXT_SUB);
      SegmentPicker({
        labels: ['看板', '任务', '日历'],
        values: ['dashboard', 'tasks', 'calendar'],
        selected: this.s.defaultView,
        onSelect: (v: string) => {
          this.patch((d: AppSettings) => {
            d.defaultView = v;
          });
        },
      });
      Text('每周起始').fontSize(12).fontColor(Theme.TEXT_SUB);
      SegmentPicker({
        labels: ['周日', '周一'],
        values: ['sun', 'mon'],
        selected: this.s.weekStart,
        onSelect: (v: string) => {
          this.patch((d: AppSettings) => {
            d.weekStart = v;
          });
        },
      });
      Row() {
        Text('任务列表显示已完成').fontSize(14).fontColor(Theme.TEXT).layoutWeight(1);
        Toggle({ type: ToggleType.Switch, isOn: this.s.showCompleted })
          .selectedColor(Theme.BRAND)
          .onChange((on: boolean) => {
            this.patch((d: AppSettings) => {
              d.showCompleted = on;
            });
          });
      }
      .width('100%')
      .padding({ top: 6, bottom: 2 });
    }
    .width('100%');
  }

  @Builder
  reminderSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '提醒' });
      Row() {
        Column({ space: 3 }) {
          Text('本地提醒').fontSize(14).fontColor(Theme.TEXT);
          Text('离线也能准时提醒，建议保持开启')
            .fontSize(11)
            .fontColor(Theme.TEXT_WEAK);
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1);
        Toggle({ type: ToggleType.Switch, isOn: this.s.localReminderEnabled })
          .selectedColor(Theme.BRAND)
          .onChange((on: boolean) => {
            this.patch((d: AppSettings) => {
              d.localReminderEnabled = on;
            });
          });
      }
      .width('100%');

      Text('默认提前量').fontSize(12).fontColor(Theme.TEXT_SUB);
      Flex({ wrap: FlexWrap.Wrap }) {
        ForEach(Options.REMIND_MINUTES, (m: number) => {
          Text(Options.remindLabel(m))
            .fontSize(12)
            .fontColor(this.s.defaultRemindBeforeMinutes === m ? '#FFFFFF' : Theme.TEXT_SUB)
            .backgroundColor(this.s.defaultRemindBeforeMinutes === m ? Theme.BRAND : '#F1F3F5')
            .borderRadius(8)
            .padding({ left: 10, right: 10, top: 5, bottom: 5 })
            .margin({ right: 7, bottom: 7 })
            .onClick(() => {
              this.patch((d: AppSettings) => {
                d.defaultRemindBeforeMinutes = m;
              });
            });
        }, (m: number) => `${m}`);
      }
      .width('100%');
      Text('单个任务可单独设置提前量，未设置时使用这里的默认值')
        .fontSize(11)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%');
  }

  @Builder
  focusSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '专注' });
      Text(`专注时长 ${this.s.focusMinutes} 分钟`).fontSize(13).fontColor(Theme.TEXT);
      Slider({
        value: this.s.focusMinutes,
        min: 5,
        max: 90,
        step: 5,
        style: SliderStyle.OutSet,
      })
        .selectedColor(Theme.BRAND)
        .onChange((v: number) => {
          this.patch((d: AppSettings) => {
            d.focusMinutes = Math.round(v);
          });
        });
      Text(`休息时长 ${this.s.focusBreakMinutes} 分钟`).fontSize(13).fontColor(Theme.TEXT);
      Slider({
        value: this.s.focusBreakMinutes,
        min: 1,
        max: 30,
        step: 1,
        style: SliderStyle.OutSet,
      })
        .selectedColor(Theme.OK)
        .onChange((v: number) => {
          this.patch((d: AppSettings) => {
            d.focusBreakMinutes = Math.round(v);
          });
        });
    }
    .width('100%');
  }

  @Builder
  lunarSection() {
    Column({ space: 10 }) {
      SectionTitle({ title: '农历与节假日' });
      Text('数据来源').fontSize(12).fontColor(Theme.TEXT_SUB);
      SegmentPicker({
        labels: ['服务端代理', '自定义接口'],
        values: ['backend', 'custom'],
        selected: this.s.lunarSource,
        onSelect: (v: string) => {
          this.patch((d: AppSettings) => {
            d.lunarSource = v;
          });
        },
      });
      if (this.s.lunarSource === 'custom') {
        TextInput({ placeholder: '农历接口地址', text: this.s.lunarApiBase })
          .height(40)
          .borderRadius(10)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.patch((d: AppSettings) => {
              d.lunarApiBase = v;
            });
          });
        TextInput({ placeholder: '节假日接口地址', text: this.s.holidayApiBase })
          .height(40)
          .borderRadius(10)
          .backgroundColor('#F5F6F8')
          .onChange((v: string) => {
            this.patch((d: AppSettings) => {
              d.holidayApiBase = v;
            });
          });
      }
      Text('农历日期、节气、传统节日在本机离线计算，断网也能看；宜忌与神位需要联网获取')
        .fontSize(11)
        .fontColor(Theme.TEXT_WEAK);
    }
    .width('100%');
  }

  @Builder
  accountSection() {
    Column({ space: 0 }) {
      SectionTitle({ title: '账号与数据' });
      SettingRow({
        label: '当前账号',
        value: Prefs.username(),
        showArrow: false,
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '修改密码',
        value: '网页端',
        onTap: () => {
          this.changePassword();
        },
      });
      Divider().color(Theme.BORDER).strokeWidth(0.5);
      SettingRow({
        label: '重置日历订阅令牌',
        value: '失效旧地址',
        onTap: () => {
          this.resetFeedToken();
        },
      });
    }
    .width('100%');
  }
}
