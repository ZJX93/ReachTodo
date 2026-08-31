import AbilityConstant from '@ohos.app.ability.AbilityConstant';
import UIAbility from '@ohos.app.ability.UIAbility';
import Want from '@ohos.app.ability.Want';
import window from '@ohos.window';
import hilog from '@ohos.hilog';
import { Prefs } from '../common/Prefs';
import { AppStore } from '../stores/AppStore';

const DOMAIN: number = 0x0001;
const TAG: string = 'Reach';

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    // 顺序要求：持久化必须在任何页面构建之前初始化完成，
    // 否则首帧读到的 token / serverUrl 会是空值，页面会闪一下登录页。
    Prefs.init();
    AppStore.attachContext(this.context);
    AppStore.installUnauthorizedHandler();
    hilog.info(DOMAIN, TAG, 'EntryAbility onCreate');
  }

  onDestroy(): void {
    hilog.info(DOMAIN, TAG, 'EntryAbility onDestroy');
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    windowStage.loadContent('pages/Index', (err) => {
      if (err.code) {
        hilog.error(DOMAIN, TAG, 'loadContent failed: %{public}s', JSON.stringify(err));
        return;
      }
      hilog.info(DOMAIN, TAG, 'loadContent succeeded');
    });
  }

  onWindowStageDestroy(): void {
    hilog.info(DOMAIN, TAG, 'onWindowStageDestroy');
  }

  onForeground(): void {
    // 回到前台时重排本地提醒：任务可能在别的端被改过，
    // 不重排会出现「已完成的任务还在提醒」。失败静默，不打扰用户。
    if (AppStore.isLoggedIn()) {
      AppStore.syncReminders().catch(() => {
      });
    }
  }

  onBackground(): void {
  }
}
