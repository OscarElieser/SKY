plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
// Firma release solo por variables de entorno, sin subir llaves privadas a Git.
val skyKeyStorePath = providers.environmentVariable("SKY_ANDROID_RELEASE_KEYSTORE").orNull
val skyStorePassword = providers.environmentVariable("SKY_ANDROID_RELEASE_STORE_PASSWORD").orNull
val skyKeyAlias = providers.environmentVariable("SKY_ANDROID_RELEASE_KEY_ALIAS").orNull
val skyKeyPassword = providers.environmentVariable("SKY_ANDROID_RELEASE_KEY_PASSWORD").orNull
val skyHasReleaseSigning = listOf(
    skyKeyStorePath, skyStorePassword, skyKeyAlias, skyKeyPassword
).all { !it.isNullOrBlank() }
if (providers.environmentVariable("SKY_ANDROID_REQUIRE_SIGNED_RELEASE").orNull == "true") {
    check(skyHasReleaseSigning && file(skyKeyStorePath!!).isFile) {
        "No hay configuracion completa de firma release SKY. Se prohibe distribuir sin firma."
    }
}
android {
    namespace = "ni.sky.mobileagent"
    compileSdk = 35
    defaultConfig {
        applicationId = "ni.sky.mobileagent"
        minSdk = 26
        targetSdk = 35
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        versionCode = 53
        versionName = "0.8.40"
    }
    // El paquete distribuible no declara servicios de accesibilidad.
    // La variante assistive queda separada para revisión y pruebas explícitas.
    flavorDimensions += "capabilities"
    productFlavors {
        create("standard") {
            dimension = "capabilities"
            buildConfigField("boolean", "ENABLE_TEXT_ASSIST", "false")
        }
        create("assistive") {
            dimension = "capabilities"
            buildConfigField("boolean", "ENABLE_TEXT_ASSIST", "true")
        }
    }
    signingConfigs {
        if (skyHasReleaseSigning) {
            create("skyRelease") {
                storeFile = file(skyKeyStorePath!!)
                storePassword = skyStorePassword
                keyAlias = skyKeyAlias
                keyPassword = skyKeyPassword
                enableV1Signing = false
                enableV2Signing = true
                enableV3Signing = true
            }
        }
    }
    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            if (skyHasReleaseSigning) {
                signingConfig = signingConfigs.getByName("skyRelease")
            }
        }
    }
    buildFeatures {
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
