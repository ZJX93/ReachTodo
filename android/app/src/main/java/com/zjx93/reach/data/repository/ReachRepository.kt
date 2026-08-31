package com.zjx93.reach.data.repository

import com.zjx93.reach.data.local.UserPrefs
import com.zjx93.reach.data.model.*
import com.zjx93.reach.data.remote.ApiService
import com.zjx93.reach.data.remote.RetrofitClient
import com.zjx93.reach.data.remote.Session
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import retrofit2.HttpException
import java.io.IOException

/** 统一封装网络请求，返回 Result<T> 并给出可读错误信息。 */
class ReachRepository {

    private suspend fun api() = RetrofitClient.api(UserPrefs.serverUrlFlow.first())

    private suspend fun <T> run(block: suspend (api: ApiService) -> T): Result<T> =
        withContext(Dispatchers.IO) {
            try {
                Result.success(block(api()))
            } catch (e: HttpException) {
                Result.failure(Exception(parseError(e.response()?.errorBody()?.string()) ?: "请求失败 (${e.code()})"))
            } catch (e: IOException) {
                Result.failure(Exception("网络异常，请检查服务器地址或网络连接"))
            } catch (e: Exception) {
                Result.failure(e)
            }
        }

    private fun parseError(json: String?): String? {
        if (json.isNullOrBlank()) return null
        return try {
            val j = JSONObject(json)
            when (val d = j.opt("detail")) {
                is JSONArray -> d.optJSONObject(0)?.optString("msg")
                is String -> d
                else -> j.optString("detail", null)
            }
        } catch (_: Exception) {
            null
        }
    }

    // ---------------- 认证 ----------------
    suspend fun login(username: String, password: String): Result<TokenOut> = run { a ->
        a.login(UserCreate(username, null, password)).also {
            Session.token = it.accessToken
            UserPrefs.setToken(it.accessToken)
        }
    }

    suspend fun register(username: String, email: String?, password: String): Result<TokenOut> = run { a ->
        a.register(UserCreate(username, email, password)).also {
            Session.token = it.accessToken
            UserPrefs.setToken(it.accessToken)
        }
    }

    suspend fun me(): Result<UserOut> = run { it.me() }
    suspend fun updateEmail(email: String?): Result<UserOut> = run { it.updateMe(UserUpdate(email)) }
    suspend fun changePassword(old: String, new: String): Result<OkResponse> =
        run { it.changePassword(PasswordChange(old, new)) }

    suspend fun logout() {
        Session.token = ""
        UserPrefs.clearToken()
    }

    // ---------------- 维度 ----------------
    suspend fun categories(): Result<List<CategoryOut>> = run { it.categories() }

    // ---------------- 任务 ----------------
    suspend fun tasks(status: String? = null): Result<List<TaskOut>> = run { it.tasks(status) }
    suspend fun createTask(body: TaskCreate): Result<TaskOut> = run { it.createTask(body) }
    suspend fun updateTask(id: Int, body: TaskUpdate): Result<TaskOut> = run { it.updateTask(id, body) }
    suspend fun deleteTask(id: Int): Result<Unit> = run { it.deleteTask(id) }

    // ---------------- 四象限 ----------------
    suspend fun tasksMatrix(): Result<List<MatrixQuadrant>> = run { it.tasksMatrix() }

    // ---------------- 目标 ----------------
    suspend fun goals(): Result<List<GoalOut>> = run { it.goals() }
    suspend fun goalsBoard(): Result<List<GoalBoardItem>> = run { it.goalsBoard() }
    suspend fun createGoal(body: GoalCreate): Result<GoalOut> = run { it.createGoal(body) }
    suspend fun updateGoal(id: Int, body: GoalUpdate): Result<GoalOut> = run { it.updateGoal(id, body) }
    suspend fun deleteGoal(id: Int): Result<Unit> = run { it.deleteGoal(id) }

    // ---------------- 记录 ----------------
    suspend fun records(date: String? = null): Result<List<RecordOut>> = run { it.records(date) }
    suspend fun recordsCalendar(year: Int, month: Int): Result<List<CalendarDay>> =
        run { it.recordsCalendar(year, month) }

    suspend fun createRecord(body: RecordCreate): Result<RecordOut> = run { it.createRecord(body) }
    suspend fun updateRecord(id: Int, body: RecordUpdate): Result<RecordOut> = run { it.updateRecord(id, body) }
    suspend fun deleteRecord(id: Int): Result<Unit> = run { it.deleteRecord(id) }

    // ---------------- 模板 ----------------
    suspend fun templates(): Result<List<TemplateOut>> = run { it.templates() }

    // ---------------- 专注 ----------------
    suspend fun createFocus(body: FocusSessionCreate): Result<FocusSessionOut> = run { it.createFocus(body) }
    suspend fun focusSessions(): Result<List<FocusSessionOut>> = run { it.focusSessions() }

    // ---------------- 统计 ----------------
    suspend fun statsSummary(): Result<StatsSummary> = run { it.statsSummary() }

    // ---------------- 农历 / 节假日 ----------------
    suspend fun lunar(date: String): Result<LunarInfo> = run { it.lunar(date) }
    suspend fun holidays(year: Int): Result<Map<String, HolidayInfo>> = run { it.holidays(year) }
}
