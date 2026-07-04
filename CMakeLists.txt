cmake_minimum_required(VERSION 3.25)

project(FantarealHuskarUI VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.7 REQUIRED COMPONENTS Core Quick Network)

qt_standard_project_setup(REQUIRES 6.7)

set(HUSKARUI_ROOT "$ENV{HUSKARUI_ROOT}" CACHE PATH "Path to a HuskarUI source checkout; leave empty to use find_package(HuskarUI)")
get_filename_component(FANTAREAL_DEFAULT_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

if(HUSKARUI_ROOT AND EXISTS "${HUSKARUI_ROOT}/CMakeLists.txt")
    set(BUILD_HUSKARUI_GALLERY OFF CACHE BOOL "Build HuskarUI Gallery." FORCE)
    add_subdirectory("${HUSKARUI_ROOT}" "${CMAKE_BINARY_DIR}/_huskarui")
else()
    find_package(HuskarUI REQUIRED)
endif()

set_source_files_properties(qml/Global.qml PROPERTIES
    QT_QML_SINGLETON_TYPE TRUE
)

qt_add_executable(FantarealHuskarUI
    cpp/main.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
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
        qml/pages/PresetPage.qml
        qml/pages/MemoryPage.qml
        qml/pages/WorldbookPage.qml
        qml/pages/RoutesPage.qml
        qml/pages/WorkshopPage.qml
        qml/pages/PluginsPage.qml
)

target_include_directories(FantarealHuskarUI PRIVATE cpp)

target_link_libraries(FantarealHuskarUI PRIVATE
    Qt6::Quick
    Qt6::Network
    HuskarUIBasic
    $<$<BOOL:${BUILD_HUSKARUI_STATIC_LIBRARY}>:HuskarUIImplPlugin>
    $<$<BOOL:${BUILD_HUSKARUI_STATIC_LIBRARY}>:HuskarUIBasicPlugin>
)

set_target_properties(FantarealHuskarUI PROPERTIES
    WIN32_EXECUTABLE TRUE
)

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

add_executable(FantarealBridgeSettingsSaveTest
    tests/settings_save_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeSettingsSaveTest PRIVATE cpp)

target_link_libraries(FantarealBridgeSettingsSaveTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeSettingsSaveTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeSettingsSaveTest COMMAND FantarealBridgeSettingsSaveTest)

add_executable(FantarealBridgeChatSendTest
    tests/chat_send_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeChatSendTest PRIVATE cpp)

target_link_libraries(FantarealBridgeChatSendTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeChatSendTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeChatSendTest COMMAND FantarealBridgeChatSendTest)

add_executable(FantarealBridgeChatGenerateTest
    tests/chat_generate_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeChatGenerateTest PRIVATE cpp)

target_link_libraries(FantarealBridgeChatGenerateTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeChatGenerateTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeChatGenerateTest COMMAND FantarealBridgeChatGenerateTest)

add_executable(FantarealBridgeChatAsyncTest
    tests/chat_async_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeChatAsyncTest PRIVATE cpp)

target_link_libraries(FantarealBridgeChatAsyncTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeChatAsyncTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeChatAsyncTest COMMAND FantarealBridgeChatAsyncTest)

add_executable(FantarealBridgeChatOutputSplitTest
    tests/chat_output_split_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeChatOutputSplitTest PRIVATE cpp)

target_link_libraries(FantarealBridgeChatOutputSplitTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeChatOutputSplitTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeChatOutputSplitTest COMMAND FantarealBridgeChatOutputSplitTest)

add_executable(FantarealBridgeChatEndConversationTest
    tests/chat_end_conversation_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeChatEndConversationTest PRIVATE cpp)

target_link_libraries(FantarealBridgeChatEndConversationTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeChatEndConversationTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeChatEndConversationTest COMMAND FantarealBridgeChatEndConversationTest)

add_executable(FantarealBridgeRouteSaveTest
    tests/route_save_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeRouteSaveTest PRIVATE cpp)

target_link_libraries(FantarealBridgeRouteSaveTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeRouteSaveTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeRouteSaveTest COMMAND FantarealBridgeRouteSaveTest)

add_executable(FantarealBridgeCardSaveTest
    tests/card_save_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeCardSaveTest PRIVATE cpp)

target_link_libraries(FantarealBridgeCardSaveTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeCardSaveTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeCardSaveTest COMMAND FantarealBridgeCardSaveTest)

add_executable(FantarealBridgePersonaSyncTest
    tests/persona_sync_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgePersonaSyncTest PRIVATE cpp)

target_link_libraries(FantarealBridgePersonaSyncTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgePersonaSyncTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgePersonaSyncTest COMMAND FantarealBridgePersonaSyncTest)

add_executable(FantarealBridgeWorldbookSaveTest
    tests/worldbook_save_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeWorldbookSaveTest PRIVATE cpp)

target_link_libraries(FantarealBridgeWorldbookSaveTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeWorldbookSaveTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeWorldbookSaveTest COMMAND FantarealBridgeWorldbookSaveTest)

add_executable(FantarealBridgeMemorySaveTest
    tests/memory_save_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeMemorySaveTest PRIVATE cpp)

target_link_libraries(FantarealBridgeMemorySaveTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeMemorySaveTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeMemorySaveTest COMMAND FantarealBridgeMemorySaveTest)

add_executable(FantarealBridgePresetSaveTest
    tests/preset_save_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgePresetSaveTest PRIVATE cpp)

target_link_libraries(FantarealBridgePresetSaveTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgePresetSaveTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgePresetSaveTest COMMAND FantarealBridgePresetSaveTest)

add_executable(FantarealBridgeImportAssetsTest
    tests/import_assets_test.cpp
    cpp/fantarealbridge.h
    cpp/fantarealbridge.cpp
)

target_include_directories(FantarealBridgeImportAssetsTest PRIVATE cpp)

target_link_libraries(FantarealBridgeImportAssetsTest PRIVATE Qt6::Core Qt6::Network)

target_compile_definitions(FantarealBridgeImportAssetsTest PRIVATE
    FANTAREAL_DEFAULT_ROOT="${FANTAREAL_DEFAULT_ROOT}"
)

add_test(NAME FantarealBridgeImportAssetsTest COMMAND FantarealBridgeImportAssetsTest)
