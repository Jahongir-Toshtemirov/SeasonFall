package com.seasonfall.app

import android.content.Context
import android.content.SharedPreferences
import java.util.Calendar

object Prefs {
    private const val NAME = "seasonfall"

    const val SEASON_WINTER = "winter"
    const val SEASON_SPRING = "spring"
    const val SEASON_SUMMER = "summer"
    const val SEASON_AUTUMN = "autumn"
    const val SEASON_AUTO = "auto"

    private fun sp(ctx: Context): SharedPreferences =
        ctx.getSharedPreferences(NAME, Context.MODE_PRIVATE)

    fun season(ctx: Context): String =
        sp(ctx).getString("season", SEASON_AUTO) ?: SEASON_AUTO

    fun setSeason(ctx: Context, value: String) {
        sp(ctx).edit().putString("season", value).apply()
    }

    /** 1..100 — mapped to a small particle budget for phones. */
    fun density(ctx: Context): Int = sp(ctx).getInt("density", 35)

    fun setDensity(ctx: Context, value: Int) {
        sp(ctx).edit().putInt("density", value.coerceIn(1, 100)).apply()
    }

    /** 0..100 → speed multiplier roughly 0.4..1.6 */
    fun speed(ctx: Context): Int = sp(ctx).getInt("speed", 45)

    fun setSpeed(ctx: Context, value: Int) {
        sp(ctx).edit().putInt("speed", value.coerceIn(0, 100)).apply()
    }

    fun speedMul(ctx: Context): Float = 0.4f + speed(ctx) / 100f * 1.2f

    fun resolvedSeason(ctx: Context): String {
        val s = season(ctx)
        if (s != SEASON_AUTO) return s
        return when (Calendar.getInstance().get(Calendar.MONTH) + 1) {
            12, 1, 2 -> SEASON_WINTER
            3, 4, 5 -> SEASON_SPRING
            6, 7, 8 -> SEASON_SUMMER
            else -> SEASON_AUTUMN
        }
    }

    /** Hard cap — phones stay cool. */
    fun particleBudget(ctx: Context): Int {
        val d = density(ctx)
        return (12 + d * 0.48f).toInt().coerceIn(12, 60)
    }
}
