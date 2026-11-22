package com.seasonfall.app

import android.app.WallpaperManager
import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class SettingsActivity : AppCompatActivity() {

    private val seasonKeys = listOf(
        Prefs.SEASON_WINTER,
        Prefs.SEASON_SPRING,
        Prefs.SEASON_SUMMER,
        Prefs.SEASON_AUTUMN,
        Prefs.SEASON_AUTO,
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            setContentView(R.layout.activity_settings)
            wireUi()
        } catch (t: Throwable) {
            Toast.makeText(this, "SeasonFall failed to open: ${t.message}", Toast.LENGTH_LONG)
                .show()
            finish()
        }
    }

    private fun wireUi() {
        val seasonSpinner = findViewById<Spinner>(R.id.seasonSpinner)
        val densitySeek = findViewById<SeekBar>(R.id.densitySeek)
        val speedSeek = findViewById<SeekBar>(R.id.speedSeek)
        val setBtn = findViewById<Button>(R.id.setWallpaperBtn)

        seasonSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            resources.getStringArray(R.array.seasons)
        )
        seasonSpinner.setSelection(seasonKeys.indexOf(Prefs.season(this)).coerceAtLeast(0), false)
        densitySeek.progress = Prefs.density(this)
        speedSeek.progress = Prefs.speed(this)

        seasonSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(
                parent: AdapterView<*>?,
                view: android.view.View?,
                position: Int,
                id: Long
            ) {
                if (position in seasonKeys.indices) {
                    Prefs.setSeason(this@SettingsActivity, seasonKeys[position])
                }
            }

            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        densitySeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) Prefs.setDensity(this@SettingsActivity, progress)
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        speedSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                if (fromUser) Prefs.setSpeed(this@SettingsActivity, progress)
            }

            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        setBtn.setOnClickListener { offerLiveWallpaper() }
    }

    private fun offerLiveWallpaper() {
        try {
            val intent = Intent(WallpaperManager.ACTION_CHANGE_LIVE_WALLPAPER).apply {
                putExtra(
                    WallpaperManager.EXTRA_LIVE_WALLPAPER_COMPONENT,
                    ComponentName(this@SettingsActivity, SeasonFallWallpaperService::class.java)
                )
            }
            startActivity(intent)
        } catch (_: Exception) {
            try {
                startActivity(Intent(WallpaperManager.ACTION_LIVE_WALLPAPER_CHOOSER))
            } catch (_: Exception) {
                Toast.makeText(
                    this,
                    "Open Settings → Wallpaper → Live wallpapers → SeasonFall",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
}
