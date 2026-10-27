plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.compose.compiler)
}

android {
    namespace = "io.github.mesteriis.rune.qa.compose"
    compileSdk = 37
    defaultConfig {
        applicationId = "io.github.mesteriis.rune.qa.compose"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "1.0-qa"
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    lint { warningsAsErrors = true; disable += "AndroidGradlePluginVersion" }
}

// This independent editor is a disposable QA tool, never a Rune product variant/dependency.
androidComponents.beforeVariants(androidComponents.selector().withBuildType("release")) { it.enable = false }

dependencies {
    implementation(libs.activity)
    implementation(libs.compose.foundation)
}

// Lock the separate fixture graph without changing Rune dependency resolution.
dependencyLocking { lockAllConfigurations() }
