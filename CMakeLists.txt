cmake_minimum_required(VERSION 3.25)

project(FantarealHuskarUI VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.7 REQUIRED COMPONENTS Core Quick Network Sql)

qt_standard_project_setup(REQUIRES 6.7)

set(FANTAREAL_QT_RUNTIME_PATH "$<TARGET_FILE_DIR:Qt6::Core>")

function(fantareal_configure_windows_qt_runtime target_name)
    if(WIN32)
        set_property(TARGET ${target_name} PROPERTY
            VS_DEBUGGER_ENVIRONMENT "PATH=${FANTAREAL_QT_RUNTIME_PATH};%PATH%"
        )
    endif()
endfunction()

function(fantareal_add_bridge_test test_name)
    add_test(NAME ${test_name} COMMAND ${test_name})
    if(WIN32)
        set_tests_properties(${test_name} PROPERTIES
            ENVIRONMENT_MODIFICATION "PATH=path_list_prepend:${FANTAREAL_QT_RUNTIME_PATH}"
        )
    endif()
    fantareal_configure_windows_qt_runtime(${test_name})
endfunction()

set(HUSKARUI_ROOT "$ENV{HUSKARUI_ROOT}" CACHE PATH "Path to a HuskarUI source checkout; leave empty to use find_package(HuskarUI)")
get_filename_component(FANTAREAL_DEFAULT_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

if(HUSKARUI_ROOT AND EXISTS "${HUSKARUI_ROOT}/CMakeLists.txt")
    set(BUILD_HUSKARUI_GALLERY OFF CACHE BOOL "Build HuskarUI Gallery." FORCE)
    add_subdirectory("${HUSKARUI_ROOT}" "${CMAKE_BINARY_DIR}/_huskarui")
else()
    find_package(HuskarUI REQUIRED)
endif()

if(TARGET HuskarUI::Basic)
    set(FANTAREAL_HUSKARUI_BASIC_TARGET HuskarUI::Basic)
else()
    set(FANTAREAL_HUSKARUI_BASIC_TARGET HuskarUIBasic)
endif()

set_source_files_properties(qml/Global.qml PROPERTIES
    QT_QML_SINGLETON_TYPE TRUE
)

qt_add_executable(FantarealHuskarUI
    cpp/main.cpp
)

add_library(FantarealCore STATIC
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
    cpp/card_authoring/cardauthoringapplyplanner.h
    cpp/card_authoring/cardauthoringapplyplanner.cpp
    cpp/card_authoring/cardauthoringcandidateprocessor.h
    cpp/card_authoring/cardauthoringcandidateprocessor.cpp
    cpp/card_authoring/cardauthoringcompiler.h
    cpp/card_authoring/cardauthoringcompiler.cpp
    cpp/card_authoring/cardauthoringmodels.h
    cpp/card_authoring/cardauthoringmodels.cpp
    cpp/card_authoring/cardauthoringpaths.h
    cpp/card_authoring/cardauthoringpaths.cpp
    cpp/card_authoring/cardauthoringpromptpack.h
    cpp/card_authoring/cardauthoringpromptpack.cpp
    cpp/card_authoring/cardauthoringprojectstore.h
    cpp/card_authoring/cardauthoringprojectstore.cpp
    cpp/card_authoring/cardauthoringservice.h
    cpp/card_authoring/cardauthoringservice.cpp
    cpp/database/databasemodels.h
    cpp/database/databasepaths.h
    cpp/database/databasepaths.cpp
    cpp/database/databaserepository.h
    cpp/database/databaserepository.cpp
    cpp/database/databaseservice.h
    cpp/database/databaseservice.cpp
    cpp/database/legacystatejournaladapter.h
    cpp/database/legacystatejournaladapter.cpp
)

set(FANTAREAL_CARD_AUTHORING_PROMPT_FILES
    resources/card_authoring/prompts/human_character_system/candidate_rules.md
    resources/card_authoring/prompts/human_character_system/case_reference.md
    resources/card_authoring/prompts/human_character_system/container_router.md
    resources/card_authoring/prompts/human_character_system/database_designer.md
    resources/card_authoring/prompts/human_character_system/deep_reference.md
    resources/card_authoring/prompts/human_character_system/fa_container_deep_router.md
    resources/card_authoring/prompts/human_character_system/humanizer_guard.md
    resources/card_authoring/prompts/human_character_system/orchestration_planner.md
    resources/card_authoring/prompts/human_character_system/question_bank_reference.md
    resources/card_authoring/prompts/human_character_system/README.md
    resources/card_authoring/prompts/human_character_system/runtime_package.md
    resources/card_authoring/prompts/human_character_system/wheelchair_core.md
    resources/card_authoring/prompts/human_character_system/worldbook_preset_memory.md
)

qt_add_resources(FantarealCore "card_authoring_prompts"
    PREFIX "/"
    FILES
        ${FANTAREAL_CARD_AUTHORING_PROMPT_FILES}
)

target_include_directories(FantarealCore PUBLIC cpp)

target_link_libraries(FantarealCore PUBLIC
    Qt6::Core
    Qt6::Network
    Qt6::Sql
)

target_compile_definitions(FantarealCore PUBLIC
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

qt_add_qml_module(FantarealHuskarUI
    URI Fantareal
    VERSION 1.0
    RESOURCE_PREFIX "/"
    QML_FILES
        qml/FantarealApp.qml
        qml/Global.qml
        qml/controls/AppNavItem.qml
        qml/controls/FirstLaunchDisclaimerModal.qml
        qml/controls/GlassCard.qml
        qml/controls/SettingField.qml
        qml/controls/SmoothWheelArea.qml
        qml/controls/SummaryRows.qml
        qml/controls/StatPill.qml
        qml/pages/HomePage.qml
        qml/pages/ChatPage.qml
        qml/pages/SettingsPage.qml
        qml/pages/CardsPage.qml
        qml/pages/CardAuthoringPage.qml
        qml/pages/DatabasePage.qml
        qml/pages/PresetPage.qml
        qml/pages/MemoryPage.qml
        qml/pages/WorldbookPage.qml
        qml/pages/RoutesPage.qml
        qml/pages/WorkshopPage.qml
        qml/pages/PluginsPage.qml
)

target_include_directories(FantarealHuskarUI PRIVATE cpp)

target_link_libraries(FantarealHuskarUI PRIVATE
    FantarealCore
    Qt6::Quick
    Qt6::Network
    ${FANTAREAL_HUSKARUI_BASIC_TARGET}
    $<$<BOOL:${BUILD_HUSKARUI_STATIC_LIBRARY}>:HuskarUIImplPlugin>
    $<$<BOOL:${BUILD_HUSKARUI_STATIC_LIBRARY}>:HuskarUIBasicPlugin>
)

set_target_properties(FantarealHuskarUI PROPERTIES
    WIN32_EXECUTABLE TRUE
)

fantareal_configure_windows_qt_runtime(FantarealHuskarUI)

if(NOT HUSKARUI_PLUGIN_OUTPUT_DIRECTORY)
    set(QML_IMPORT_PATH ${CMAKE_BINARY_DIR}/HuskarUI/qml CACHE STRING "" FORCE)
else()
    set(QML_IMPORT_PATH ${HUSKARUI_PLUGIN_OUTPUT_DIRECTORY}/HuskarUI/qml CACHE STRING "" FORCE)
endif()

target_compile_definitions(FantarealHuskarUI PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

if(BUILD_HUSKARUI_STATIC_LIBRARY)
    target_compile_definitions(FantarealHuskarUI PRIVATE BUILD_HUSKARUI_STATIC_LIBRARY)
endif()

enable_testing()

function(fantareal_add_core_test test_name test_source)
    add_executable(${test_name} ${test_source})
    target_link_libraries(${test_name} PRIVATE FantarealCore)
    fantareal_add_bridge_test(${test_name})
endfunction()

fantareal_add_core_test(FantarealBridgeSettingsSaveTest tests/settings_save_test.cpp)
fantareal_add_core_test(FantarealBridgeChatSendTest tests/chat_send_test.cpp)
fantareal_add_core_test(FantarealBridgeChatGenerateTest tests/chat_generate_test.cpp)
fantareal_add_core_test(FantarealBridgeChatAsyncTest tests/chat_async_test.cpp)
fantareal_add_core_test(FantarealBridgeChatOutputSplitTest tests/chat_output_split_test.cpp)
fantareal_add_core_test(FantarealBridgeChatEndConversationTest tests/chat_end_conversation_test.cpp)
fantareal_add_core_test(FantarealBridgeRouteSaveTest tests/route_save_test.cpp)
fantareal_add_core_test(FantarealBridgeCardSaveTest tests/card_save_test.cpp)
fantareal_add_core_test(FantarealBridgePersonaSyncTest tests/persona_sync_test.cpp)
fantareal_add_core_test(FantarealBridgeWorldbookSaveTest tests/worldbook_save_test.cpp)
fantareal_add_core_test(FantarealBridgeMemorySaveTest tests/memory_save_test.cpp)
fantareal_add_core_test(FantarealBridgePresetSaveTest tests/preset_save_test.cpp)
fantareal_add_core_test(FantarealBridgeImportAssetsTest tests/import_assets_test.cpp)
fantareal_add_core_test(FantarealDatabaseServiceTest tests/database_service_test.cpp)
fantareal_add_core_test(FantarealBridgeDatabaseTest tests/database_bridge_test.cpp)
fantareal_add_core_test(FantarealCardAuthoringServiceTest tests/card_authoring_service_test.cpp)
fantareal_add_core_test(FantarealBridgeCardAuthoringTest tests/card_authoring_bridge_test.cpp)
