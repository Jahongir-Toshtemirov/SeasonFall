package com.seasonfall.app

import android.graphics.Canvas
import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.service.wallpaper.WallpaperService
import android.view.SurfaceHolder
import kotlin.math.max

/**
 * Live wallpaper — Android only draws while the home screen / picker preview
 * is visible. Waits for a real surface before animating so the wallpaper
 * chooser does not spin on "Loading…" forever.
 */
class SeasonFallWallpaperService : WallpaperService() {

    override fun onCreateEngine(): Engine = FallEngine()

    private inner class FallEngine : Engine() {
        private val handler = Handler(Looper.getMainLooper())
        private val engine = ParticleEngine()
        private var visible = false
        private var surfaceReady = false
        private var width = 1
        private var height = 1
        private var lastNs = 0L

        // ~24 fps
        private val frameMs = 42L

        private val tick = object : Runnable {
            override fun run() {
                if (!visible || !surfaceReady) return
                try {
                    val now = System.nanoTime()
                    val dt = if (lastNs == 0L) 0.016f
                    else ((now - lastNs) / 1_000_000_000f).coerceIn(0.008f, 0.05f)
                    lastNs = now
                    engine.tick(dt)
                    drawFrame()
                } catch (_: Throwable) {
                    // Never let a frame kill the wallpaper service.
                }
                if (visible && surfaceReady) {
                    handler.postDelayed(this, frameMs)
                }
            }
        }

        override fun onCreate(surfaceHolder: SurfaceHolder) {
            super.onCreate(surfaceHolder)
            setTouchEventsEnabled(false)
            setOffsetNotificationsEnabled(false)
            reloadPrefs()
        }

        override fun onDestroy() {
            handler.removeCallbacksAndMessages(null)
            super.onDestroy()
        }

        override fun onVisibilityChanged(visible: Boolean) {
            this.visible = visible
            if (visible) {
                reloadPrefs()
                maybeStart()
            } else {
                handler.removeCallbacks(tick)
            }
        }

        override fun onSurfaceCreated(holder: SurfaceHolder) {
            super.onSurfaceCreated(holder)
            surfaceReady = true
            // Immediate first paint so the picker leaves "Loading…"
            drawFrame()
            maybeStart()
        }

        override fun onSurfaceDestroyed(holder: SurfaceHolder) {
            surfaceReady = false
            handler.removeCallbacks(tick)
            super.onSurfaceDestroyed(holder)
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
            surfaceReady = true
            drawFrame()
            maybeStart()
        }

        private fun maybeStart() {
            handler.removeCallbacks(tick)
            if (visible && surfaceReady) {
                lastNs = 0L
                handler.post(tick)
            }
        }

        private fun reloadPrefs() {
            try {
                engine.configure(
                    Prefs.resolvedSeason(this@SeasonFallWallpaperService),
                    Prefs.particleBudget(this@SeasonFallWallpaperService),
                    Prefs.speedMul(this@SeasonFallWallpaperService),
                )
                engine.resize(width, height)
            } catch (_: Throwable) {
            }
        }

        private fun drawFrame() {
            var canvas: Canvas? = null
            try {
                canvas = surfaceHolder.lockCanvas()
                if (canvas != null) {
                    try {
                        engine.draw(canvas)
                    } catch (_: Throwable) {
                        canvas.drawColor(Color.rgb(28, 40, 58))
                    }
                }
            } catch (_: Throwable) {
            } finally {
                if (canvas != null) {
                    try {
                        surfaceHolder.unlockCanvasAndPost(canvas)
                    } catch (_: Throwable) {
                    }
                }
            }
        }
    }
}
