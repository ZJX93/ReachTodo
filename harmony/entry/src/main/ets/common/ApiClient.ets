/**
 * HTTP 客户端：所有网络请求的唯一出口。
 *
 * 收口在一处的价值：
 * - Bearer 令牌注入只写一遍，不会有某个页面忘记带；
 * - 401 统一清会话，令牌过期后自动回到登录页，而不是每页各弹一个报错；
 * - 后端 `{"detail": "..."}` 统一翻译成人话，UI 层拿到的 message 可直接展示；
 * - 网络异常（DNS/超时/自签证书）与业务错误用同一个 `ApiError` 表达，
 *   页面只需 catch 一种类型。
 */
import http from '@ohos.net.http';
import { Prefs } from './Prefs';

/** 统一错误类型。`status` 为 0 表示请求未到达服务端（网络层失败）。 */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

interface ErrorBody {
  detail?: string;
}

/** 查询串构造器：自动 URL 编码，跳过 undefined/空值，支持同名重复参数（tag）。 */
export class Query {
  private parts: string[] = [];

  str(key: string, value?: string | null): Query {
    if (value !== undefined && value !== null && value.length > 0) {
      this.parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
    }
    return this;
  }

  num(key: string, value?: number | null): Query {
    if (value !== undefined && value !== null) {
      this.parts.push(`${encodeURIComponent(key)}=${value}`);
    }
    return this;
  }

  bool(key: string, value?: boolean): Query {
    if (value !== undefined && value !== null) {
      this.parts.push(`${encodeURIComponent(key)}=${value ? 'true' : 'false'}`);
    }
    return this;
  }

  list(key: string, values?: string[]): Query {
    if (values !== undefined && values !== null) {
      for (const v of values) {
        this.str(key, v);
      }
    }
    return this;
  }

  build(): string {
    return this.parts.length === 0 ? '' : '?' + this.parts.join('&');
  }
}

/** 401 回调：由 App 层注册（清会话 + 回登录页），避免网络层反向依赖 UI。 */
type UnauthorizedHandler = () => void;

class ApiClientClass {
  private onUnauthorized: UnauthorizedHandler | null = null;

  setUnauthorizedHandler(handler: UnauthorizedHandler): void {
    this.onUnauthorized = handler;
  }

  /** 发送请求并返回响应体文本（2xx）。非 2xx / 网络失败统一抛 `ApiError`。 */
  private async send(
    method: http.RequestMethod,
    path: string,
    body?: string,
    withAuth: boolean = true
  ): Promise<string> {
    const base: string = Prefs.serverUrl();
    if (!base) {
      throw new ApiError(0, '尚未配置服务器地址，请先在「我的 → 服务器地址」中填写');
    }

    const header: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (withAuth) {
      const token: string = Prefs.token();
      if (token.length > 0) {
        header['Authorization'] = `Bearer ${token}`;
      }
    }

    const options: http.HttpRequestOptions = {
      method: method,
      header: header,
      expectDataType: http.HttpDataType.STRING,
      connectTimeout: 10000,
      readTimeout: 20000,
    };
    if (body !== undefined) {
      options.extraData = body;
    }

    const task = http.createHttp();
    let code: number = 0;
    let text: string = '';
    try {
      const resp: http.HttpResponse = await task.request(base + path, options);
      code = resp.responseCode;
      text = typeof resp.result === 'string' ? resp.result as string : '';
    } catch (err) {
      // 这里只可能是网络层异常（DNS / 连接被拒 / 超时 / TLS 校验失败）
      const e = err as Error;
      throw new ApiError(0, `无法连接服务器：${e?.message ?? '未知网络错误'}`);
    } finally {
      task.destroy();
    }

    if (code >= 200 && code < 300) {
      return text;
    }
    if (code === 401) {
      // 令牌失效：先清会话再抛错，防止后续请求继续用坏令牌打服务端
      Prefs.clearSession();
      if (this.onUnauthorized) {
        this.onUnauthorized();
      }
      throw new ApiError(401, '登录已过期，请重新登录');
    }
    throw new ApiError(code, ApiClientClass.explain(code, text));
  }

  /** 把后端错误体翻成一句可直接展示的话。 */
  private static explain(code: number, text: string): string {
    if (text.length > 0) {
      try {
        const body = JSON.parse(text) as ErrorBody;
        // detail 可能是字符串（HTTPException）或数组（pydantic 校验错误）
        if (typeof body.detail === 'string' && body.detail.length > 0) {
          return body.detail;
        }
      } catch (e) {
        // 不是 JSON（如网关返回的 HTML 502 页面），忽略，走下面的兜底文案
      }
    }
    if (code === 403) {
      return '没有权限执行该操作';
    }
    if (code === 404) {
      return '请求的内容不存在';
    }
    if (code === 429) {
      return '操作过于频繁，请稍后再试';
    }
    if (code >= 500) {
      return `服务器错误（${code}）`;
    }
    return `请求失败（${code}）`;
  }

  async get<T>(path: string): Promise<T> {
    const text: string = await this.send(http.RequestMethod.GET, path);
    return JSON.parse(text) as T;
  }

  async post<T>(path: string, body: object, withAuth: boolean = true): Promise<T> {
    const text: string = await this.send(
      http.RequestMethod.POST, path, JSON.stringify(body), withAuth
    );
    return JSON.parse(text) as T;
  }

  /** 无响应体（或不关心响应体）的 POST，例如注册设备、清空回收站。 */
  async postVoid(path: string, body: object): Promise<void> {
    await this.send(http.RequestMethod.POST, path, JSON.stringify(body));
  }

  async put<T>(path: string, body: object): Promise<T> {
    const text: string = await this.send(
      http.RequestMethod.PUT, path, JSON.stringify(body)
    );
    return JSON.parse(text) as T;
  }

  async patch<T>(path: string, body: object): Promise<T> {
    const text: string = await this.send(
      http.RequestMethod.PATCH, path, JSON.stringify(body)
    );
    return JSON.parse(text) as T;
  }

  /** DELETE 通常返回 204 空体，不能对空串做 JSON.parse。 */
  async del(path: string): Promise<void> {
    await this.send(http.RequestMethod.DELETE, path);
  }

  /** 不带鉴权的 GET，用于 `/health` 探活（连通性测试）。 */
  async ping(): Promise<string> {
    return await this.send(http.RequestMethod.GET, '/health', undefined, false);
  }
}

export const ApiClient: ApiClientClass = new ApiClientClass();
