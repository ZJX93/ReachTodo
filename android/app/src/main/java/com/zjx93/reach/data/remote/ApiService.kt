package com.zjx93.reach.data.remote

import com.zjx93.reach.data.model.*
import retrofit2.http.*

interface ApiService {

    // ---------------- 认证 ----------------
    @POST("/api/auth/register")
    suspend fun register(@Body body: UserCreate): TokenOut

    @POST("/api/auth/login")
    suspend fun login(@Body body: UserCreate): TokenOut

    @GET("/api/auth/me")
    suspend fun me(): UserOut

    @PATCH("/api/auth/me")
    suspend fun updateMe(@Body body: UserUpdate): UserOut

    @POST("/api/auth/me/password")
    suspend fun changePassword(@Body body: PasswordChange): OkResponse

    // ---------------- 维度 ----------------
    @GET("/api/categories")
    suspend fun categories(): List<CategoryOut>

    // ---------------- 任务 ----------------
    @GET("/api/tasks")
    suspend fun tasks(
        @Query("status") status: String? = null,
        @Query("limit") limit: Int = 500,
        @Query("offset") offset: Int = 0,
    ): List<TaskOut>

    @POST("/api/tasks")
    suspend fun createTask(@Body body: TaskCreate): TaskOut

    @PUT("/api/tasks/{id}")
    suspend fun updateTask(@Path("id") id: Int, @Body body: TaskUpdate): TaskOut

    @DELETE("/api/tasks/{id}")
    suspend fun deleteTask(@Path("id") id: Int)

    @GET("/api/tasks/matrix")
    suspend fun tasksMatrix(): List<MatrixQuadrant>

    // ---------------- 目标 ----------------
    @GET("/api/goals")
    suspend fun goals(): List<GoalOut>

    @GET("/api/goals/board")
    suspend fun goalsBoard(): List<GoalBoardItem>

    @POST("/api/goals")
    suspend fun createGoal(@Body body: GoalCreate): GoalOut

    @PUT("/api/goals/{id}")
    suspend fun updateGoal(@Path("id") id: Int, @Body body: GoalUpdate): GoalOut

    @DELETE("/api/goals/{id}")
    suspend fun deleteGoal(@Path("id") id: Int)

    // ---------------- 记录 ----------------
    @GET("/api/records")
    suspend fun records(@Query("date") date: String? = null): List<RecordOut>

    @GET("/api/records/calendar")
    suspend fun recordsCalendar(
        @Query("year") year: Int,
        @Query("month") month: Int,
    ): List<CalendarDay>

    @POST("/api/records")
    suspend fun createRecord(@Body body: RecordCreate): RecordOut

    @PUT("/api/records/{id}")
    suspend fun updateRecord(@Path("id") id: Int, @Body body: RecordUpdate): RecordOut

    @DELETE("/api/records/{id}")
    suspend fun deleteRecord(@Path("id") id: Int)

    // ---------------- 模板 ----------------
    @GET("/api/templates")
    suspend fun templates(): List<TemplateOut>

    // ---------------- 专注 ----------------
    @POST("/api/focus")
    suspend fun createFocus(@Body body: FocusSessionCreate): FocusSessionOut

    @GET("/api/focus")
    suspend fun focusSessions(): List<FocusSessionOut>

    // ---------------- 统计 ----------------
    @GET("/api/stats/summary")
    suspend fun statsSummary(): StatsSummary

    // ---------------- 农历 / 节假日 ----------------
    @GET("/api/lunar/{date}")
    suspend fun lunar(@Path("date") date: String): LunarInfo

    @GET("/api/holidays/{year}")
    suspend fun holidays(@Path("year") year: Int): Map<String, HolidayInfo>

    // ---------------- 设备推送 ----------------
    @POST("/api/devices/register")
    suspend fun registerDevice(@Body body: DeviceRegister): OkResponse

    @POST("/api/devices/unregister")
    suspend fun unregisterDevice(@Body body: DeviceRegister): OkResponse
}
