import com.android.build.api.artifact.SingleArtifact
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
}

val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties().apply {
    if (keystorePropertiesFile.exists()) {
        keystorePropertiesFile.inputStream().use(::load)
    }
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
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        // Present only on machines that carry a keystore; release stays buildable (unsigned) without one.
        if (keystorePropertiesFile.exists()) {
            create("release") {
                storeFile = rootProject.file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.findByName("release")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
        create("profile") {
            initWith(getByName("release"))
            applicationIdSuffix = ".profile"
            versionNameSuffix = "-profile"
            signingConfig = signingConfigs.getByName("debug")
            isDebuggable = false
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
        // Keyboard views are built programmatically with injected metrics; they are never inflated.
        disable += "ViewConstructor"
    }
}

dependencies {
    testImplementation(libs.junit4)
    androidTestImplementation(libs.androidx.test.core)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.rules)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.uiautomator)
}

/**
 * Fails the build if Rune ever gains a permission or starts logging.
 * Both are product invariants: the keyboard is fully offline and never logs editor text.
 */
abstract class PrivacyGateTask : DefaultTask() {
    @get:InputFile
    abstract val mergedManifest: RegularFileProperty

    @get:InputDirectory
    abstract val sourceDirectory: DirectoryProperty

    @TaskAction
    fun verify() {
        val manifest = mergedManifest.get().asFile.readText()
        if (manifest.contains("<uses-permission")) {
            val declared = PERMISSION_PATTERN.findAll(manifest).map { it.groupValues[1] }.toList()
            throw GradleException(
                "Rune must ship without permissions, but the merged manifest declares: $declared",
            )
        }

        val offenders = sourceDirectory.asFileTree
            .matching { include("**/*.kt", "**/*.java") }
            .filter { file -> LOG_PATTERN.containsMatchIn(file.readText()) }
            .map { file -> file.path }
            .sorted()
        if (offenders.isNotEmpty()) {
            throw GradleException(
                "Rune must not log; remove the logging calls in:\n" + offenders.joinToString("\n"),
            )
        }
    }

    private companion object {
        val PERMISSION_PATTERN = Regex("""<uses-permission[^>]*android:name="([^"]+)"""")
        val LOG_PATTERN = Regex("""android\.util\.Log|(^|[^\w.])Log\.[vdiwe]\(""", RegexOption.MULTILINE)
    }
}

androidComponents {
    onVariants(selector().withBuildType("release")) { variant ->
        registerPrivacyGate(variant)
    }
    onVariants(selector().withBuildType("profile")) { variant ->
        registerPrivacyGate(variant)
    }
}

fun com.android.build.api.variant.ApplicationAndroidComponentsExtension.registerPrivacyGate(
    variant: com.android.build.api.variant.ApplicationVariant,
) {
        val variantName = variant.name.replaceFirstChar(Char::uppercaseChar)
        val gate = tasks.register<PrivacyGateTask>("privacyGate$variantName") {
            group = "verification"
            description = "Verifies that Rune declares no permissions and contains no logging."
            mergedManifest.set(variant.artifacts.get(SingleArtifact.MERGED_MANIFEST))
            sourceDirectory.set(layout.projectDirectory.dir("src/main/java"))
        }
        tasks.named("check").configure { dependsOn(gate) }
}
