plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "ni.sky.mobileagent"
    compileSdk = 35
    defaultConfig {
        applicationId = "ni.sky.mobileagent"
        minSdk = 26
        targetSdk = 35
        versionCode = 6
        versionName = "0.5.1"
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
}
