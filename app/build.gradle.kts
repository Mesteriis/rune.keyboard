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
        versionCode = 2
        versionName = "0.2.0"
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
            matchingFallbacks += listOf("release")
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
    implementation(project(":runtime-llama"))
    testImplementation(libs.junit4)
    androidTestImplementation(libs.androidx.test.core)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.rules)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.uiautomator)
}

/**
 * Fails the build if Rune's single network permission or privacy boundaries drift.
 * INTERNET is used only by explicit model downloads outside the IME package.
 */
abstract class PrivacyGateTask : DefaultTask() {
    @get:InputFile
    abstract val mergedManifest: RegularFileProperty

    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val sourceDirectories: ConfigurableFileCollection

    @TaskAction
    fun verify() {
        val manifest = mergedManifest.get().asFile.readText()
        val declared = PERMISSION_PATTERN.findAll(manifest).map { it.groupValues[1] }.toList()
        if (declared != listOf("android.permission.INTERNET")) {
            throw GradleException(
                "Rune must ship with exactly android.permission.INTERNET, but declares: $declared",
            )
        }
        if (!manifest.contains("android:usesCleartextTraffic=\"false\"")) {
            throw GradleException("Rune must disable cleartext traffic")
        }
        if (!manifest.contains("android:allowBackup=\"false\"")) {
            throw GradleException("Rune must disable backup")
        }

        val offenders = sourceDirectories.asFileTree
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
        val PERMISSION_PATTERN = Regex("""<uses-permission(?:-sdk-\d+)?[^>]*android:name="([^"]+)"""")
        val LOG_PATTERN = Regex("""android\.util\.Log|(^|[^\w.])Log\.[vdiwe]\(""", RegexOption.MULTILINE)
    }
}

abstract class ImeIntelligenceBoundaryTask : DefaultTask() {
    @get:InputDirectory
    abstract val imeSourceDirectory: DirectoryProperty

    @TaskAction
    fun verify() {
        val forbidden = Regex(
            """DownloadManager|java\.net\.|android\.net\.|\b(?:Socket|ServerSocket|URL)\s*\(|intelligence|runtime[-_.]llama""",
        )
        val offenders = imeSourceDirectory.asFileTree
            .matching { include("**/*.kt", "**/*.java") }
            .filter { forbidden.containsMatchIn(it.readText()) }
            .map { it.path }
            .sorted()
        if (offenders.isNotEmpty()) {
            throw GradleException(
                "IME sources must not depend on model delivery, runtime, or network APIs:\n" +
                    offenders.joinToString("\n"),
            )
        }
    }
}

abstract class ForbiddenRuntimeDependencyTask : DefaultTask() {
    @get:Input
    abstract val componentNames: ListProperty<String>

    @TaskAction
    fun verify() {
        val forbidden = Regex(
            """(?i)(okhttp|retrofit|ktor-client|volley|work-runtime|kotlinx-coroutines|firebase|analytics|appcenter|sentry)""",
        )
        val offenders = componentNames.get().filter(forbidden::containsMatchIn).sorted()
        if (offenders.isNotEmpty()) {
            throw GradleException("Forbidden runtime dependencies: ${offenders.joinToString()}")
        }
    }
}

val imeIntelligenceBoundary = tasks.register<ImeIntelligenceBoundaryTask>("imeIntelligenceBoundary") {
    group = "verification"
    description = "Keeps model delivery, runtime, and network APIs out of ime/**."
    imeSourceDirectory.set(layout.projectDirectory.dir("src/main/java/io/github/mesteriis/rune/keyboard/ime"))
}

val forbiddenRuntimeDependencies = tasks.register<ForbiddenRuntimeDependencyTask>("forbiddenRuntimeDependencies") {
    group = "verification"
    description = "Rejects HTTP clients, analytics SDKs, WorkManager, and coroutines."
    val releaseRuntime = configurations.named("releaseRuntimeClasspath")
    componentNames.set(providers.provider {
        releaseRuntime.get().incoming.resolutionResult.allComponents
            .map { it.id.displayName }
            .sorted()
    })
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
            description = "Verifies Rune's exact permission set, privacy flags, and logging boundary."
            mergedManifest.set(variant.artifacts.get(SingleArtifact.MERGED_MANIFEST))
            sourceDirectories.from(
                layout.projectDirectory.dir("src/main/java"),
                layout.projectDirectory.dir("src/debug/java"),
                layout.projectDirectory.dir("src/profile/java"),
                layout.projectDirectory.dir("src/release/java"),
                project(":runtime-llama").layout.projectDirectory.dir("src/main/java"),
            )
        }
        tasks.named("check").configure {
            dependsOn(
                gate,
                imeIntelligenceBoundary,
                forbiddenRuntimeDependencies,
                project(":runtime-llama").tasks.named("nativeSymbolGate"),
            )
        }
}
