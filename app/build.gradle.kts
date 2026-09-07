import com.android.build.api.artifact.SingleArtifact
import com.android.build.api.artifact.ScopedArtifact
import com.android.build.api.variant.ScopedArtifacts
import java.util.Properties
import javax.inject.Inject
import org.gradle.process.ExecOperations

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
    buildFeatures { aidl = true }

    androidResources {
        // Packed lexicon components are read-only APK mappings opened through AssetManager.openFd.
        noCompress += listOf("trie", "lengths", "ranks")
    }

    defaultConfig {
        applicationId = "io.github.mesteriis.rune.keyboard"
        minSdk = 26
        targetSdk = 37
        versionCode = 4
        versionName = "0.3.1"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        // UTP collects failure screenshots/XML before uninstalling the test application.
        testInstrumentationRunnerArguments["additionalTestOutputDir"] =
            "/sdcard/Android/data/io.github.mesteriis.rune.keyboard/files/instrumentation-failures"
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

/** Uses AGP's pre-R8 classes and the final APK/mapping, so obfuscation cannot hide the recorder. */
abstract class TypingDiagnosticsPackagingTask : DefaultTask() {
    @get:Input abstract val variantName: Property<String>
    @get:InputFile abstract val verifier: RegularFileProperty
    @get:InputFile abstract val mergedManifest: RegularFileProperty
    @get:InputDirectory abstract val apkDirectory: DirectoryProperty
    @get:Optional @get:InputFile abstract val mappingFile: RegularFileProperty
    @get:Classpath abstract val classJars: ListProperty<RegularFile>
    @get:Classpath abstract val classDirectories: ListProperty<Directory>
    @get:Inject abstract val execOperations: ExecOperations

    @TaskAction fun verify() {
        val arguments = mutableListOf("python3", verifier.get().asFile.absolutePath,
            "--variant", variantName.get(), "--manifest", mergedManifest.get().asFile.absolutePath,
            "--apk-dir", apkDirectory.get().asFile.absolutePath)
        mappingFile.orNull?.let { arguments.addAll(listOf("--mapping", it.asFile.absolutePath)) }
        (classJars.get().map { it.asFile } + classDirectories.get().map { it.asFile }).forEach {
            arguments.addAll(listOf("--classes", it.absolutePath))
        }
        execOperations.exec { commandLine(arguments) }.assertNormalExitValue()
    }
}

val typingDiagnosticsBoundaryFixtures = tasks.register<Exec>("typingDiagnosticsBoundaryFixtures") {
    group = "verification"
    inputs.files(rootProject.file("tools/test_typing_diagnostics_boundary.py"),
        rootProject.file("tools/verify-scoring-boundaries.py"),
        rootProject.file("tools/test_typing_diagnostics_packaging.py"),
        rootProject.file("tools/typing_diagnostics_packaging.py"))
    workingDir(rootProject.projectDir)
    environment("PYTHONDONTWRITEBYTECODE", "1")
    commandLine("python3", "-m", "unittest", "discover", "-s", "tools", "-p", "test_typing_diagnostics_*.py")
}

val imeIntelligenceBoundary = tasks.register<Exec>("imeIntelligenceBoundary") {
    group = "verification"
    description = "Checks exact IME/client, service, and neutral storage dependency boundaries."
    for (sourceSet in listOf("main", "debug", "release", "profile")) {
        inputs.dir(layout.projectDirectory.dir("src/$sourceSet/java"))
        inputs.files(fileTree("src/$sourceSet/aidl") { include("**/*.aidl") })
    }
    inputs.dir(project(":runtime-llama").layout.projectDirectory.dir("src/main/java"))
    inputs.file(rootProject.file("tools/verify-scoring-boundaries.py"))
    commandLine("python3", rootProject.file("tools/verify-scoring-boundaries.py"),
        "--root", rootProject.projectDir, "--self-test")
    dependsOn(typingDiagnosticsBoundaryFixtures)
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

// Runtime/model changes cannot silently retain a previously qualified build identity.
val qualificationArtifacts = tasks.register<Exec>("qualificationArtifacts") {
    group = "verification"
    workingDir(rootProject.projectDir)
    commandLine("python3", rootProject.file("tools/qualification_artifacts.py"))
}
tasks.named("preBuild").configure { dependsOn(qualificationArtifacts) }

androidComponents {
    onVariants(selector().all()) { variant ->
        val name = variant.name.replaceFirstChar(Char::uppercaseChar)
        val diagnostics = tasks.register<TypingDiagnosticsPackagingTask>("typingDiagnosticsPackaging$name") {
            group = "verification"
            variantName.set(variant.name)
            verifier.set(rootProject.file("tools/typing_diagnostics_packaging.py"))
            mergedManifest.set(variant.artifacts.get(SingleArtifact.MERGED_MANIFEST))
            apkDirectory.set(variant.artifacts.get(SingleArtifact.APK))
            if (variant.name != "debug") mappingFile.set(variant.artifacts.get(SingleArtifact.OBFUSCATION_MAPPING_FILE))
            dependsOn(typingDiagnosticsBoundaryFixtures)
        }
        variant.artifacts.forScope(ScopedArtifacts.Scope.PROJECT).use(diagnostics)
            .toGet(ScopedArtifact.CLASSES, TypingDiagnosticsPackagingTask::classJars,
                TypingDiagnosticsPackagingTask::classDirectories)
    }
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
            dependsOn("typingDiagnosticsPackaging$variantName", "typingDiagnosticsPackagingDebug")
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
