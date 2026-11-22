package com.seasonfall.app

import android.app.WallpaperManager
import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.SeekBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.seasonfall.app.databinding.ActivitySettingsBinding

class SettingsActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySettingsBinding

    private val seasonKeys = listOf(
        Prefs.SEASON_WINTER,
        Prefs.SEASON_SPRING,
        Prefs.SEASON_SUMMER,
        Prefs.SEASON_AUTUMN,
        Prefs.SEASON_AUTO,
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.seasonSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            resources.getStringArray(R.array.seasons)
        )
        val idx = seasonKeys.indexOf(Prefs.season(this)).coerceAtLeast(0)
        binding.seasonSpinner.setSelection(idx)

        binding.densitySeek.progress = Prefs.density(this)
        binding.speedSeek.progress = Prefs.speed(this)

        binding.seasonSpinner.onItemSelectedListener =
            SimpleItemSelected { position ->
                Prefs.setSeason(this, seasonKeys[position])
            }

        binding.densitySeek.setOnSeekBarChangeListener(SimpleSeek {
            Prefs.setDensity(this, it)
        })
        binding.speedSeek.setOnSeekBarChangeListener(SimpleSeek {
            Prefs.setSpeed(this, it)
        })

        binding.setWallpaperBtn.setOnClickListener { offerLiveWallpaper() }
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

private class SimpleSeek(val onChange: (Int) -> Unit) : SeekBar.OnSeekBarChangeListener {
    override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
        if (fromUser) onChange(progress)
    }

    override fun onStartTrackingTouch(seekBar: SeekBar?) {}
    override fun onStopTrackingTouch(seekBar: SeekBar?) {}
}

private class SimpleItemSelected(val onSelect: (Int) -> Unit) :
    android.widget.AdapterView.OnItemSelectedListener {
    override fun onItemSelected(
        parent: android.widget.AdapterView<*>?,
        view: android.view.View?,
        position: Int,
        id: Long
    ) = onSelect(position)

    override fun onNothingSelected(parent: android.widget.AdapterView<*>?) {}
}
