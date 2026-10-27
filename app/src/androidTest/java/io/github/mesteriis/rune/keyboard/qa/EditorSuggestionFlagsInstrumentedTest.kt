package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith

/** Resident real IME, remote editor, and a positive-control model Binder observer. */
@RunWith(AndroidJUnit4::class)
class EditorSuggestionFlagsInstrumentedTest : ImeTestBase() {
    @Test fun noSuggestionsRetainsComposingAndMechanicsWithoutCandidatesOrLearning() {
        LiveFakeModelBinderFixture.install(driver).use { fixture ->
            fixture.proveNormalPipelineObservers()
            fixture.verifyNoSuggestionsComposingSearchAndMechanics()
        }
    }

    @Test fun noSuggestionsInIncognitoStillSuppressesCandidatesAndLearning() {
        LiveFakeModelBinderFixture.install(driver).use { fixture ->
            fixture.proveNormalPipelineObservers()
            fixture.verifyNoSuggestionsComposingSearchAndMechanics("private_no_suggestions")
        }
    }

    @Test fun autoCompleteSearchSubmitsOriginalWithoutModelWork() = verify("autocomplete")
    @Test fun filterSearchSubmitsOriginalWithoutModelWork() = verify("filter")

    private fun verify(mode: String) {
        LiveFakeModelBinderFixture.install(driver).use { fixture ->
            fixture.proveNormalPipelineObservers()
            fixture.verifyApplicationCompletionSearch(mode)
        }
    }
}
