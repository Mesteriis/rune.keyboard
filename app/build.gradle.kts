plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "io.github.mesteriis.rune.keyboard"
    compileSdk = 37

    defaultConfig {
        applicationId = "io.github.mesteriis.rune.keyboard"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    lint {
        abortOnError = true
        checkReleaseBuilds = true
        warningsAsErrors = true
        // Toolchain versions are deliberately pinned and upgraded as a reviewed change.
        disable += "AndroidGradlePluginVersion"
    }
}

dependencies {
    testImplementation(libs.junit4)
}
