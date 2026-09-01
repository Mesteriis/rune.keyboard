plugins {
    id("com.android.library")
}

android {
    namespace = "io.github.mesteriis.rune.runtime.llama"
    compileSdk = 37
    ndkVersion = "29.0.14206865"

    defaultConfig {
        minSdk = 26
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk {
            abiFilters += setOf("arm64-v8a", "x86_64")
        }
        externalNativeBuild {
            cmake {
                arguments += listOf(
                    "-DANDROID_PLATFORM=android-26",
                    "-DANDROID_STL=c++_shared",
                )
                cppFlags += listOf("-std=c++17", "-fexceptions", "-frtti")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.31.6"
        }
    }
}

dependencies {
    testImplementation(libs.junit4)
    androidTestImplementation(libs.androidx.test.core)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.ext.junit)
}

tasks.register<Exec>("nativeSymbolGate") {
    group = "verification"
    description = "Checks Rune JNI dependencies, exported entry point, and forbidden symbols."
    dependsOn("assembleRelease")
    commandLine("bash", rootProject.file("tools/verify-native-runtime.sh").absolutePath)
}
