plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.seasonfall.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.seasonfall.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 131
        versionName = "1.3.1"
    }

    buildTypes {
        release {
            // Sideload-friendly FOSS signing. Keep minify OFF — R8 has been
            // a common cause of blank/forever-loading launches on OEMs.
            signingConfig = signingConfigs.getByName("debug")
            isMinifyEnabled = false
            isShrinkResources = false
        }
        debug {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        viewBinding = false
    }
    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
}
