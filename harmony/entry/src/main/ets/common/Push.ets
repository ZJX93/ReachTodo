/**
 * 华为推送（Push Kit）令牌注册。
 *
 * 这是「云端提醒」通道：后端调度器扫到即将到期的任务后，通过 Push Kit
 * 下发通知（见 `server/app/push_hms.py`）。它与本地提醒（`Reminder.ets`）
 * 互为备份——本地提醒解决离线与未配置推送的场景，云推送解决
 * 「应用被彻底冻结 / 换机后未打开过应用」的场景。
 *
 * 关键设计：**取不到 token 一律静默降级**。自建服务器很可能没配 HMS 凭证，
 * 设备也可能未登录华为账号；此时应用必须照常可用，只是少一条推送通道。
 */
import { pushService } from '@kit.PushKit';
import { Api } from './Api';
import { Prefs } from './Prefs';

export class Push {
  /**
   * 获取推送令牌并上报后端。
   * @returns 上报成功返回 token，否则返回空串
   */
  static async register(deviceName: string): Promise<string> {
    const token: string = await Push.fetchToken();
    if (token.length === 0) {
      return '';
    }
    try {
      await Api.registerDevice({
        token: token,
        platform: 'harmony',
        device_name: deviceName,
      });
      Prefs.setPushToken(token);
      return token;
    } catch (e) {
      // 后端未开推送 / 网络异常：不影响使用，下次启动再试
      return '';
    }
  }

  /** 退出登录时解绑，避免推送发到已登出的设备。 */
  static async unregister(): Promise<void> {
    const token: string = Prefs.pushToken();
    if (token.length === 0) {
      return;
    }
    try {
      await Api.unregisterDevice({ token: token, platform: 'harmony' });
    } catch (e) {
      // 忽略：服务端侧的失效 token 会在推送失败后自行清理
    }
    Prefs.setPushToken('');
  }

  /**
   * 取 Push Kit token。
   *
   * 以下任一条件不满足都会抛错，全部按「无推送通道」处理：
   * 工程未接入 AGC（缺 `agconnect-services.json`）、设备未登录华为账号、
   * 推送服务未开通、无网络。
   */
  private static async fetchToken(): Promise<string> {
    try {
      const token: string = await pushService.getToken();
      return token ?? '';
    } catch (e) {
      return '';
    }
  }
}
