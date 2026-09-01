package io.github.mesteriis.rune.keyboard.qa

import org.junit.Before
import org.junit.Rule

abstract class ImeTestBase {
    protected val driver = ImeTestDriver()

    @get:Rule
    val failureArtifacts = ImeFailureArtifacts(driver)

    @Before
    fun prepareIme() = driver.setUp()
}
