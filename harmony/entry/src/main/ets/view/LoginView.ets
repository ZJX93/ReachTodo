/**
 * 登录 / 注册。
 *
 * 自托管应用的登录页必须先解决「服务器在哪」——把服务器地址放在账号之上，
 * 并提供「测试连接」，否则用户填对了账号密码却连不上，只会得到一句
 * 「登录失败」，无从判断是地址错还是密码错。
 */
import { Api } from '../common/Api';
import { Prefs } from '../common/Prefs';
import { Theme } from '../common/Theme';
import { errorText, toast } from '../common/Toast';
import { AppStore } from '../stores/AppStore';

@Component
export struct LoginView {
  @State private mode: string = 'login'; // login | register
  @State private serverUrl: string = '';
  @State private username: string = '';
  @State private password: string = '';
  @State private email: string = '';
  @State private busy: boolean = false;
  @State private testing: boolean = false;
  @State private message: string = '';

  aboutToAppear(): void {
    this.serverUrl = Prefs.serverUrl();
  }

  private async testConnection(): Promise<void> {
    Prefs.setServerUrl(this.serverUrl);
    this.testing = true;
    this.message = '';
    try {
      await Api.health();
      this.message = '服务器连接正常';
      toast('服务器连接正常');
    } catch (err) {
      this.message = errorText(err as object);
    } finally {
      this.testing = false;
    }
  }

  private async submit(): Promise<void> {
    if (this.username.trim().length === 0 || this.password.length === 0) {
      this.message = '请填写用户名与密码';
      return;
    }
    if (this.mode === 'register' && this.password.length < 6) {
      this.message = '密码至少 6 位';
      return;
    }
    Prefs.setServerUrl(this.serverUrl);
    this.busy = true;
    this.message = '';
    try {
      if (this.mode === 'login') {
        await AppStore.login(this.username.trim(), this.password);
      } else {
        await AppStore.register(this.username.trim(), this.password, this.email.trim());
      }
      // 初始化失败不应该把用户挡在门外：令牌已就绪，进入应用后各页面会自行重试
      await AppStore.bootstrap();
    } catch (err) {
      this.message = errorText(err as object);
    } finally {
      this.busy = false;
    }
  }

  build() {
    Scroll() {
      Column({ space: 14 }) {
        Column({ space: 6 }) {
          Text('抵达')
            .fontSize(34)
            .fontWeight(FontWeight.Bold)
            .fontColor(Theme.BRAND_DARK);
          Text('维度分块 · 四象限 · 关联目标')
            .fontSize(13)
            .fontColor(Theme.TEXT_SUB);
        }
        .width('100%')
        .padding({ top: 56, bottom: 18 })
        .alignItems(HorizontalAlign.Center);

        Column({ space: 10 }) {
          Text('服务器地址').fontSize(12).fontColor(Theme.TEXT_SUB);
          TextInput({ placeholder: 'https://reach.example.com', text: this.serverUrl })
            .type(InputType.Normal)
            .height(44)
            .borderRadius(10)
            .backgroundColor('#F5F6F8')
            .onChange((v: string) => {
              this.serverUrl = v;
            });
          Row({ space: 10 }) {
            Button(this.testing ? '测试中…' : '测试连接')
              .fontSize(13)
              .height(34)
              .backgroundColor('#EEF2FF')
              .fontColor(Theme.BRAND_DARK)
              .enabled(!this.testing)
              .onClick(() => {
                this.testConnection();
              });
            Text('留空则无法请求任何接口')
              .fontSize(11)
              .fontColor(Theme.TEXT_WEAK)
              .layoutWeight(1);
          }
          .width('100%');
        }
        .width('100%')
        .alignItems(HorizontalAlign.Start)
        .padding(14)
        .backgroundColor(Theme.CARD)
        .borderRadius(Theme.RADIUS);

        Column({ space: 10 }) {
          Row({ space: 0 }) {
            Text('登录')
              .fontSize(15)
              .fontWeight(this.mode === 'login' ? FontWeight.Bold : FontWeight.Normal)
              .fontColor(this.mode === 'login' ? Theme.BRAND : Theme.TEXT_SUB)
              .padding({ right: 18 })
              .onClick(() => {
                this.mode = 'login';
                this.message = '';
              });
            Text('注册')
              .fontSize(15)
              .fontWeight(this.mode === 'register' ? FontWeight.Bold : FontWeight.Normal)
              .fontColor(this.mode === 'register' ? Theme.BRAND : Theme.TEXT_SUB)
              .onClick(() => {
                this.mode = 'register';
                this.message = '';
              });
          }
          .width('100%');

          TextInput({ placeholder: '用户名', text: this.username })
            .height(44)
            .borderRadius(10)
            .backgroundColor('#F5F6F8')
            .onChange((v: string) => {
              this.username = v;
            });
          TextInput({ placeholder: '密码', text: this.password })
            .type(InputType.Password)
            .height(44)
            .borderRadius(10)
            .backgroundColor('#F5F6F8')
            .onChange((v: string) => {
              this.password = v;
            });
          if (this.mode === 'register') {
            TextInput({ placeholder: '邮箱（可选）', text: this.email })
              .type(InputType.Email)
              .height(44)
              .borderRadius(10)
              .backgroundColor('#F5F6F8')
              .onChange((v: string) => {
                this.email = v;
              });
          }

          if (this.message.length > 0) {
            Text(this.message).fontSize(12).fontColor(Theme.DANGER);
          }

          Button(this.busy ? '请稍候…' : (this.mode === 'login' ? '登录' : '注册并登录'))
            .width('100%')
            .height(46)
            .borderRadius(12)
            .backgroundColor(Theme.BRAND)
            .enabled(!this.busy)
            .onClick(() => {
              this.submit();
            });
        }
        .width('100%')
        .alignItems(HorizontalAlign.Start)
        .padding(14)
        .backgroundColor(Theme.CARD)
        .borderRadius(Theme.RADIUS);

        Text('数据保存在你自己的服务器上')
          .fontSize(11)
          .fontColor(Theme.TEXT_WEAK)
          .padding({ top: 8, bottom: 20 });
      }
      .width('100%')
      .padding({ left: Theme.PAGE_PADDING, right: Theme.PAGE_PADDING });
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.BG);
  }
}
