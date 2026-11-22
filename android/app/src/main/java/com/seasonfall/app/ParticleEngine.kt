package com.seasonfall.app

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

/**
 * Tiny Canvas particle field tuned for phones:
 * - hard cap ~60 particles
 * - simple shapes (circles / short strokes)
 * - no bitmaps, no OpenGL
 */
class ParticleEngine(private val rng: Random = Random.Default) {

    private data class P(
        var x: Float,
        var y: Float,
        var vx: Float,
        var vy: Float,
        var size: Float,
        var rot: Float,
        var spin: Float,
        var phase: Float,
        var kind: Int,
        var color: Int,
        var alpha: Int,
    )

    private val particles = ArrayList<P>(64)
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val path = Path()

    private var width = 1
    private var height = 1
    private var season = Prefs.SEASON_WINTER
    private var budget = 30
    private var speedMul = 1f
    private var wind = 0f

    fun resize(w: Int, h: Int) {
        width = w.coerceAtLeast(1)
        height = h.coerceAtLeast(1)
    }

    fun configure(seasonKey: String, budget: Int, speedMul: Float) {
        this.season = seasonKey
        this.budget = budget.coerceIn(8, 60)
        this.speedMul = speedMul.coerceIn(0.3f, 2f)
        while (particles.size > this.budget) particles.removeAt(particles.lastIndex)
        while (particles.size < this.budget) particles.add(spawn(top = rng.nextBoolean()))
    }

    fun tick(dt: Float) {
        if (dt <= 0f || dt > 0.1f) return
        // gentle wind drift — cheap, no gust simulation
        wind += (rng.nextFloat() - 0.5f) * 4f * dt
        wind = wind.coerceIn(-28f, 28f)

        var i = 0
        while (i < particles.size) {
            val p = particles[i]
            val sway = sin(p.phase) * (10f + p.size)
            p.x += (p.vx + wind + sway) * dt * speedMul
            p.y += p.vy * dt * speedMul
            p.rot += p.spin * dt * speedMul
            p.phase += dt * (1.2f + p.size * 0.08f)
            val offBottom = p.y > height + 24f
            val offTop = p.y < -40f
            val offSide = p.x < -40f || p.x > width + 40f
            if (offBottom || offTop || offSide) {
                // Rising sparks recycle from the bottom; everything else from top.
                particles[i] = spawn(top = p.vy >= 0f)
            }
            i++
        }
        while (particles.size < budget) particles.add(spawn(top = true))
    }

    fun draw(canvas: Canvas) {
        // Deep soft sky — static fill, no gradients per frame.
        canvas.drawColor(Color.rgb(28, 40, 58))
        for (p in particles) {
            paint.color = p.color
            paint.alpha = p.alpha
            when (p.kind) {
                KIND_SNOW -> drawSnowflake(canvas, p)
                KIND_PETAL -> drawPetal(canvas, p)
                KIND_SPARK -> drawSpark(canvas, p)
                else -> drawLeaf(canvas, p)
            }
        }
    }

    private fun drawSnowflake(canvas: Canvas, p: P) {
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = (p.size * 0.22f).coerceAtLeast(1.2f)
        paint.strokeCap = Paint.Cap.ROUND
        val s = p.size
        canvas.save()
        canvas.translate(p.x, p.y)
        canvas.rotate(p.rot)
        for (i in 0 until 6) {
            val a = Math.toRadians(i * 60.0).toFloat()
            canvas.drawLine(0f, 0f, cos(a) * s, sin(a) * s, paint)
        }
        canvas.restore()
        paint.style = Paint.Style.FILL
    }

    private fun drawPetal(canvas: Canvas, p: P) {
        paint.style = Paint.Style.FILL
        canvas.save()
        canvas.translate(p.x, p.y)
        canvas.rotate(p.rot)
        canvas.scale(1f, 0.55f)
        canvas.drawCircle(0f, 0f, p.size, paint)
        canvas.restore()
    }

    private fun drawSpark(canvas: Canvas, p: P) {
        paint.style = Paint.Style.FILL
        canvas.drawCircle(p.x, p.y, p.size * 0.55f, paint)
        paint.alpha = (p.alpha * 0.35f).toInt()
        canvas.drawCircle(p.x, p.y, p.size * 1.3f, paint)
    }

    private fun drawLeaf(canvas: Canvas, p: P) {
        paint.style = Paint.Style.FILL
        path.reset()
        val s = p.size
        path.moveTo(0f, -s)
        path.quadTo(s * 0.7f, -s * 0.2f, 0f, s)
        path.quadTo(-s * 0.7f, -s * 0.2f, 0f, -s)
        path.close()
        canvas.save()
        canvas.translate(p.x, p.y)
        canvas.rotate(p.rot)
        canvas.drawPath(path, paint)
        canvas.restore()
    }

    private fun spawn(top: Boolean): P {
        val (kind, color, alpha, size, vyBase) = when (season) {
            Prefs.SEASON_SPRING -> Spawn(
                KIND_PETAL,
                palette(SPRING_COLORS),
                180 + rng.nextInt(60),
                5f + rng.nextFloat() * 7f,
                35f + rng.nextFloat() * 40f
            )
            Prefs.SEASON_SUMMER -> Spawn(
                KIND_SPARK,
                palette(SUMMER_COLORS),
                160 + rng.nextInt(70),
                3f + rng.nextFloat() * 5f,
                -(18f + rng.nextFloat() * 22f) // rises
            )
            Prefs.SEASON_AUTUMN -> Spawn(
                KIND_LEAF,
                palette(AUTUMN_COLORS),
                200 + rng.nextInt(40),
                7f + rng.nextFloat() * 8f,
                40f + rng.nextFloat() * 45f
            )
            else -> Spawn(
                KIND_SNOW,
                palette(WINTER_COLORS),
                200 + rng.nextInt(55),
                4f + rng.nextFloat() * 8f,
                28f + rng.nextFloat() * 40f
            )
        }
        return P(
            x = rng.nextFloat() * width,
            y = if (top) -20f - rng.nextFloat() * height * 0.2f
            else rng.nextFloat() * height,
            vx = (rng.nextFloat() - 0.5f) * 18f,
            vy = vyBase,
            size = size,
            rot = rng.nextFloat() * 360f,
            spin = (rng.nextFloat() - 0.5f) * 80f,
            phase = rng.nextFloat() * 6.28f,
            kind = kind,
            color = color,
            alpha = alpha.coerceIn(80, 255),
        )
    }

    private fun palette(colors: IntArray): Int = colors[rng.nextInt(colors.size)]

    private data class Spawn(
        val kind: Int,
        val color: Int,
        val alpha: Int,
        val size: Float,
        val vy: Float,
    )

    companion object {
        private const val KIND_SNOW = 0
        private const val KIND_PETAL = 1
        private const val KIND_SPARK = 2
        private const val KIND_LEAF = 3

        private val WINTER_COLORS = intArrayOf(
            Color.rgb(255, 255, 255),
            Color.rgb(230, 240, 255),
            Color.rgb(200, 220, 245),
        )
        private val SPRING_COLORS = intArrayOf(
            Color.rgb(255, 183, 197),
            Color.rgb(255, 158, 181),
            Color.rgb(247, 143, 167),
        )
        private val SUMMER_COLORS = intArrayOf(
            Color.rgb(255, 214, 120),
            Color.rgb(255, 236, 160),
            Color.rgb(255, 190, 92),
        )
        private val AUTUMN_COLORS = intArrayOf(
            Color.rgb(226, 88, 34),
            Color.rgb(240, 138, 44),
            Color.rgb(188, 122, 32),
            Color.rgb(245, 160, 60),
        )
    }
}
