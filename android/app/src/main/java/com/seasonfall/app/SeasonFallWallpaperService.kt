package com.seasonfall.app

import android.os.Handler
import android.os.Looper
import android.service.wallpaper.WallpaperService
import android.view.SurfaceHolder
import kotlin.math.max

/**
 * Live wallpaper — Android only draws while the home screen is visible,
 * which is the main battery win vs a floating overlay.
 *
 * Extra low-power knobs:
 * - ~24 FPS target
 * - ≤60 particles
 * - pause when invisible / screen off
 */
class SeasonFallWallpaperService : WallpaperService() {

    override fun onCreateEngine(): Engine = FallEngine()

    private inner class FallEngine : Engine() {
        private val handler = Handler(Looper.getMainLooper())
        private val engine = ParticleEngine()
        private var visible = false
        private var width = 1
        private var height = 1
        private var lastNs = 0L

        // ~24 fps — phones stay cooler than 60 fps desktop builds
        private val frameMs = 42L

        private val tick = object : Runnable {
            override fun run() {
                if (!visible) return
                val now = System.nanoTime()
                val dt = if (lastNs == 0L) 0.016f
                else ((now - lastNs) / 1_000_000_000f).coerceIn(0.008f, 0.05f)
                lastNs = now
                engine.tick(dt)
                drawFrame()
                handler.postDelayed(this, frameMs)
            }
        }

        override fun onCreate(surfaceHolder: SurfaceHolder) {
            super.onCreate(surfaceHolder)
            // Touch not needed — saves work.
            setTouchEventsEnabled(false)
            reloadPrefs()
        }

        override fun onDestroy() {
            handler.removeCallbacks(tick)
            super.onDestroy()
        }

        override fun onVisibilityChanged(visible: Boolean) {
            this.visible = visible
            handler.removeCallbacks(tick)
            if (visible) {
                reloadPrefs()
                lastNs = 0L
                handler.post(tick)
            }
        }

        override fun onSurfaceChanged(
            holder: SurfaceHolder,
            format: Int,
            width: Int,
            height: Int
        ) {
            super.onSurfaceChanged(holder, format, width, height)
            this.width = max(1, width)
            this.height = max(1, height)
            engine.resize(this.width, this.height)
            reloadPrefs()
            drawFrame()
        }

        override fun onOffsetsChanged(
            xOffset: Float,
            yOffset: Float,
            xOffsetStep: Float,
            yOffsetStep: Float,
            xPixelOffset: Int,
            yPixelOffset: Int
        ) {
            // Parallax ignored on purpose — less work on scroll.
        }

        private fun reloadPrefs() {
            engine.configure(
                Prefs.resolvedSeason(this@SeasonFallWallpaperService),
                Prefs.particleBudget(this@SeasonFallWallpaperService),
                Prefs.speedMul(this@SeasonFallWallpaperService),
            )
            engine.resize(width, height)
        }

        private fun drawFrame() {
            var canvas = null as android.graphics.Canvas?
            try {
                canvas = surfaceHolder.lockCanvas()
                if (canvas != null) {
                    engine.draw(canvas)
                }
            } catch (_: Exception) {
                // Surface gone during unlock races — ignore.
            } finally {
                if (canvas != null) {
                    try {
                        surfaceHolder.unlockCanvasAndPost(canvas)
                    } catch (_: Exception) {
                    }
                }
            }
        }
    }
}
