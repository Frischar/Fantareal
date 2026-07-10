import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    property bool initialized: false
    property bool dirty: false
    property var projectDraft: ({})
    property var projectItems: []
    property var previewResult: ({})
    property var previewGroups: []
    property var previewWarnings: []
    property var compiledResult: ({})
    property var compiledWarnings: []
    property string candidatePromptText: ""
    property string candidateCurrentView: "database"
    property string candidateThinkingMode: "deep"
    property string candidateReviewText: ""
    property var candidateReviewResult: ({})
    property var candidateCandidates: []
    property var candidateGroups: []
    property var candidateAudit: ({})
    property var copilotMessages: []
    property bool candidateAdvancedVisible: false
    property var selectedCandidateIds: []
    property string titleText: ""
    property string cardNameText: ""
    property string tagsText: ""
    property string descriptionText: ""
    property string personalityText: ""
    property string scenarioText: ""
    property string firstMessageText: ""
    property string mesExampleText: ""
    property string creatorNotesText: ""
    property var personaItems: []
    property int selectedPersonaIndex: -1
    property string personaIdText: ""
    property string personaNameText: ""
    property string personaDescriptionText: ""
    property string personaPersonalityText: ""
    property string personaScenarioText: ""
    property string personaCreatorNotesText: ""
    property string personaTagsText: ""
    property bool creativeWorkshopPresent: false
    property var creativeWorkshopDraft: ({})
    property bool creativeWorkshopEnabled: true
    property var workshopItems: []
    property int selectedWorkshopIndex: -1
    property string workshopIdText: ""
    property string workshopNameText: ""
    property bool workshopEnabled: true
    property string workshopTriggerModeText: "manual"
    property string workshopTriggerStageText: ""
    property string workshopTriggerTempMinText: "0"
    property string workshopTriggerTempMaxText: "1"
    property string workshopActionTypeText: "note"
    property string workshopPopupTitleText: ""
    property string workshopMusicPresetText: ""
    property string workshopMusicUrlText: ""
    property bool workshopAutoplay: false
    property bool workshopLoop: false
    property string workshopVolumeText: "0.7"
    property string workshopImageUrlText: ""
    property string workshopImageAltText: ""
    property string workshopNoteText: ""
    property bool databaseEnabled: true
    property string databaseNotesText: ""
    property var databaseVariables: []
    property var databaseStages: []
    property var databaseSnapshotFields: []
    property var databaseTags: []
    property int selectedVariableIndex: -1
    property int selectedStageIndex: -1
    property int selectedSnapshotFieldIndex: -1
    property int selectedTagIndex: -1
    property string variableKeyText: ""
    property string variableLabelText: ""
    property string variableTypeText: "text"
    property string variableScopeText: "role"
    property string variableInitialValueText: ""
    property string variableDescriptionText: ""
    property string variableWritePolicyText: ""
    property string variableNotesText: ""
    property string stageRoleText: "role"
    property string stageKeyText: ""
    property string stageTitleText: ""
    property string stageConditionText: ""
    property string stageActiveTagText: ""
    property string stageEmitsTagsText: ""
    property string stageDescriptionText: ""
    property string stageNotesText: ""
    property string snapshotRoleText: "role"
    property string snapshotKeyText: ""
    property string snapshotLabelText: ""
    property bool snapshotEnabled: true
    property bool snapshotDisplay: true
    property string snapshotInstructionText: ""
    property string snapshotNotesText: ""
    property string databaseTagText: ""
    property string databaseTagTitleText: ""
    property string databaseTagTriggerText: ""
    property string databaseTagTargetText: "worldbook"
    property string databaseTagDescriptionText: ""
    property string databaseTagNotesText: ""
    property var worldbookEntries: []
    property int selectedWorldbookIndex: -1
    property string worldbookIdText: ""
    property string worldbookTitleText: ""
    property string worldbookTriggerText: ""
    property string worldbookSecondaryTriggerText: ""
    property string worldbookEntryTypeText: "keyword"
    property string worldbookGroupText: ""
    property string worldbookGroupOperatorText: "and"
    property string worldbookMatchModeText: "any"
    property string worldbookSecondaryModeText: "all"
    property string worldbookContentText: ""
    property string worldbookCommentText: ""
    property string worldbookOrderText: "100"
    property string worldbookChanceText: "100"
    property string worldbookStickyTurnsText: "0"
    property string worldbookCooldownTurnsText: "0"
    property string worldbookInsertionPositionText: "after_char_defs"
    property string worldbookInjectionDepthText: "0"
    property string worldbookInjectionRoleText: "system"
    property string worldbookInjectionOrderText: "100"
    property string worldbookPromptLayerText: "follow_position"
    property string worldbookExternalSourceText: ""
    property string worldbookActivationTagsText: ""
    property bool worldbookEnabled: true
    property bool worldbookRecursiveEnabled: true
    property bool worldbookPreventFurtherRecursion: false
    property bool worldbookCaseSensitive: false
    property bool worldbookWholeWord: false
    property bool worldbookTriggerAdvancedVisible: false
    property bool worldbookInjectionAdvancedVisible: false
    property bool worldbookStateAdvancedVisible: false
    property bool worldbookSettingsVisible: false
    property string worldbookGroupFilter: "__all__"
    property string worldbookSearchText: ""
    property bool worldbookEntryPickerExpanded: false
    property var worldbookSettings: ({})
    property var presetModules: ({})
    property var presetExtraPrompts: []
    property var presetPromptGroups: []
    property string presetActivePresetId: ""
    property string presetNameText: ""
    property bool presetEnabled: true
    property string presetBaseSystemPromptText: ""
    property string selectedPresetCollection: "extra_prompts"
    property int selectedPresetItemIndex: -1
    property int selectedPresetGroupItemIndex: -1
    property string presetItemIdText: ""
    property string presetItemNameText: ""
    property string presetItemContentText: ""
    property string presetItemOrderText: "100"
    property string presetItemPlacementText: ""
    property string presetItemKindText: ""
    property string presetItemStrengthText: ""
    property string presetItemRoleText: "system"
    property string presetItemDepthText: "0"
    property string presetItemTokenBudgetText: ""
    property string presetItemActivationTagsText: ""
    property bool presetItemEnabled: true
    property bool presetItemRequired: false
    property bool presetItemAdvancedVisible: false
    property string presetGroupIdText: ""
    property string presetGroupNameText: ""
    property string presetGroupSelectionModeText: "single"
    property string presetGroupSelectedIdsText: ""
    property string presetGroupOrderText: "100"
    property bool presetGroupEnabled: true
    property string presetGroupItemIdText: ""
    property string presetGroupItemNameText: ""
    property string presetGroupItemContentText: ""
    property string presetGroupItemPlacementText: ""
    property string presetGroupItemKindText: ""
    property string presetGroupItemStrengthText: ""
    property string presetGroupItemRoleText: "system"
    property string presetGroupItemDepthText: "0"
    property string presetGroupItemTokenBudgetText: ""
    property string presetGroupItemActivationTagsText: ""
    property bool presetGroupItemEnabled: true
    property bool presetGroupItemRequired: false
    property bool presetGroupItemAdvancedVisible: false
    property var memoryItems: []
    property int selectedMemoryIndex: -1
    property string memoryIdText: ""
    property string memoryTitleText: ""
    property string memoryContentText: ""
    property string memoryTagsText: ""
    property string memoryNotesText: ""
    property string memoryStatusText: "active"
    property bool applyPersona: false
    property bool applyDatabase: true
    property bool applyWorldbook: false
    property bool applyPreset: false
    property bool applyMemory: false
    property bool previewStale: false
    property string previewDraftKey: ""
    property string previewModuleKey: ""
    property var pendingApplyDraft: ({})
    property var pendingApplyGroups: []
    property var pendingApplyPreview: ({})
    property var lastOperationResult: ({})
    readonly property var presetModuleDefs: [
        {
            "key": "no_user_speaking",
            "label": "防抢话"
        },
        {
            "key": "short_paragraph",
            "label": "短段落"
        },
        {
            "key": "long_paragraph",
            "label": "长段落"
        },
        {
            "key": "second_person",
            "label": "第二人称"
        },
        {
            "key": "third_person",
            "label": "第三人称"
        },
        {
            "key": "anti_repeat",
            "label": "抗重复"
        },
        {
            "key": "no_closing_feel",
            "label": "弱收尾"
        },
        {
            "key": "emotion_detail",
            "label": "情绪细节"
        },
        {
            "key": "multi_character_boundary",
            "label": "多角色边界"
        },
        {
            "key": "scene_continuation",
            "label": "场景延续"
        },
        {
            "key": "anti_horny",
            "label": "抗发情"
        },
        {
            "key": "anti_deification",
            "label": "抗神化"
        }
    ]

    function clone(value) {
        if (value === undefined || value === null) {
            return {};
        }
        return JSON.parse(JSON.stringify(value));
    }

    function firstObject(items) {
        if (items && items.length > 0) {
            return items[0] || {};
        }
        return {};
    }

    function paddedIndex(index) {
        const value = index + 1;
        if (value < 10) {
            return `00${value}`;
        }
        if (value < 100) {
            return `0${value}`;
        }
        return `${value}`;
    }

    function defaultVariable(index) {
        return {
            "id": `db_var_${paddedIndex(index)}`,
            "key": "",
            "label": "",
            "value_type": "text",
            "initial_value": "",
            "scope": "role",
            "description": "",
            "write_policy": "",
            "notes": ""
        };
    }

    function defaultStage(index) {
        const stageKey = `stage_${index + 1}`;
        return {
            "id": `db_stage_${paddedIndex(index)}`,
            "role_id": "role",
            "stage_key": stageKey,
            "title": "",
            "condition": "",
            "active_tag": `database.stage.role.${stageKey}`,
            "emits_tags": [`database.stage.role.${stageKey}`],
            "description": "",
            "notes": ""
        };
    }

    function defaultSnapshotField(index) {
        return {
            "id": `db_snapshot_${paddedIndex(index)}`,
            "role_id": "role",
            "key": `snapshot_${index + 1}`,
            "label": "",
            "enabled": true,
            "display": true,
            "instruction": "根据本轮上下文生成该状态快照字段。",
            "notes": ""
        };
    }

    function defaultDatabaseTag(index) {
        return {
            "id": `db_tag_${paddedIndex(index)}`,
            "tag": "",
            "title": "",
            "trigger": "",
            "target": "worldbook",
            "description": "",
            "notes": ""
        };
    }

    function defaultWorldbookEntry(index) {
        return {
            "id": `wb_entry_${paddedIndex(index)}`,
            "title": "",
            "trigger": "",
            "secondary_trigger": "",
            "entry_type": "keyword",
            "group_operator": "and",
            "match_mode": "any",
            "secondary_mode": "all",
            "group": "",
            "content": "",
            "comment": "",
            "order": 100,
            "priority": 100,
            "chance": 100,
            "sticky_turns": 0,
            "cooldown_turns": 0,
            "insertion_position": "after_char_defs",
            "injection_depth": 0,
            "injection_role": "system",
            "injection_order": 100,
            "prompt_layer": "follow_position",
            "recursive_enabled": true,
            "prevent_further_recursion": false,
            "case_sensitive": false,
            "whole_word": false,
            "external_source": "",
            "activation_tags": [],
            "enabled": true
        };
    }

    function defaultPresetItem(index, collection) {
        if (collection === "prompt_groups") {
            return {
                "id": `prompt_group_${paddedIndex(index)}`,
                "name": "",
                "enabled": true,
                "selection_mode": "single",
                "selected_ids": [],
                "items": [],
                "order": (index + 1) * 100
            };
        }
        return {
            "id": `extra_prompt_${paddedIndex(index)}`,
            "name": "",
            "content": "",
            "order": (index + 1) * 100,
            "enabled": true
        };
    }

    function defaultPresetGroupItem(index) {
        return {
            "id": `prompt_group_item_${paddedIndex(index)}`,
            "name": "",
            "content": "",
            "enabled": true
        };
    }

    function defaultMemoryItem(index) {
        return {
            "id": `memory_${paddedIndex(index)}`,
            "title": "",
            "content": "",
            "tags": [],
            "notes": "",
            "memory_status": "active"
        };
    }

    function defaultPersonaItem(index) {
        return {
            "id": `${index + 1}`,
            "name": "",
            "description": "",
            "personality": "",
            "scenario": "",
            "creator_notes": "",
            "tags": []
        };
    }

    function defaultWorkshopItem(index) {
        return {
            "id": `workshop_${paddedIndex(index)}`,
            "name": "",
            "enabled": true,
            "triggerMode": "manual",
            "triggerStage": "",
            "triggerTempMin": 0,
            "triggerTempMax": 1,
            "actionType": "note",
            "popupTitle": "",
            "musicPreset": "",
            "musicUrl": "",
            "autoplay": false,
            "loop": false,
            "volume": 0.7,
            "imageUrl": "",
            "imageAlt": "",
            "note": ""
        };
    }

    function markDirty() {
        if (initialized) {
            dirty = true;
            markPreviewStale();
        }
    }

    function markPreviewStale() {
        if (!initialized) {
            return;
        }
        if ((previewResult || {}).ok || previewGroups.length > 0) {
            previewStale = true;
        }
        previewDraftKey = "";
        previewModuleKey = "";
    }

    function splitTagsText(text) {
        const result = [];
        const parts = String(text || "").split(/[,\n;，；、]+/);
        for (let i = 0; i < parts.length; ++i) {
            const tag = parts[i].trim();
            if (tag.length > 0 && result.indexOf(tag) < 0) {
                result.push(tag);
            }
        }
        return result;
    }

    function tagsToText(tags) {
        if (!tags || tags.length === 0) {
            return "";
        }
        const result = [];
        for (let i = 0; i < tags.length; ++i) {
            const tag = String(tags[i] || "").trim();
            if (tag.length > 0) {
                result.push(tag);
            }
        }
        return result.join(", ");
    }

    function numericOrDefault(value, fallback) {
        const numericValue = Number(value);
        return isNaN(numericValue) ? fallback : numericValue;
    }

    function presetTopLabel() {
        return selectedPresetCollection === "prompt_groups" ? "预设组" : "额外提示";
    }

    function refreshProjectItems() {
        projectItems = FantarealBridge.cardAuthoringProjectItems || [];
    }

    function projectMetaText(item) {
        const variables = Number(item.variable_count || 0);
        const stages = Number(item.stage_count || 0);
        const snapshots = Number(item.snapshot_field_count || 0);
        const entries = Number(item.worldbook_entry_count || 0);
        const memories = Number(item.memory_item_count || 0);
        return `${variables} 变量 · ${stages} 阶段规则 · ${snapshots} 快照字段 · ${entries} 世界书 · ${memories} 记忆`;
    }

    function variableTitle(item, index) {
        return item.label || item.key || `变量 ${index + 1}`;
    }

    function stageTitle(item, index) {
        return item.title || item.stage_key || `阶段规则 ${index + 1}`;
    }

    function snapshotFieldTitle(item, index) {
        return item.label || item.key || `状态快照字段 ${index + 1}`;
    }

    function databaseTagTitle(item, index) {
        return item.title || item.tag || `数据库标签 ${index + 1}`;
    }

    function worldbookTitle(item, index) {
        return item.title || item.trigger || `世界书词条 ${index + 1}`;
    }

    function worldbookGroupKey(item) {
        const group = String((item || {}).group || "").trim();
        return group.length > 0 ? group : "__ungrouped__";
    }

    function worldbookGroupLabel(key) {
        if (key === "__all__") {
            return "全部";
        }
        if (key === "__ungrouped__") {
            return "未分组";
        }
        return key || "未分组";
    }

    function worldbookGroupOptions() {
        const stats = {};
        for (let i = 0; i < worldbookEntries.length; ++i) {
            const key = worldbookGroupKey(worldbookEntries[i]);
            stats[key] = (stats[key] || 0) + 1;
        }

        const keys = Object.keys(stats);
        keys.sort(function (left, right) {
            if (left === "__ungrouped__") {
                return -1;
            }
            if (right === "__ungrouped__") {
                return 1;
            }
            return String(left).localeCompare(String(right), "zh-CN", { numeric: true });
        });

        const result = [{ "key": "__all__", "label": "全部", "count": worldbookEntries.length }];
        for (let i = 0; i < keys.length; ++i) {
            result.push({
                "key": keys[i],
                "label": worldbookGroupLabel(keys[i]),
                "count": stats[keys[i]]
            });
        }
        return result;
    }

    function worldbookEntryMatchesSearch(item, index) {
        const needle = String(worldbookSearchText || "").trim().toLowerCase();
        if (needle.length === 0) {
            return true;
        }
        const haystack = [
            worldbookTitle(item || {}, index),
            (item || {}).id || "",
            (item || {}).group || "",
            (item || {}).trigger || "",
            (item || {}).secondary_trigger || "",
            (item || {}).entry_type || "",
            (item || {}).prompt_layer || "",
            (item || {}).external_source || "",
            tagsToText((item || {}).activation_tags || []),
            (item || {}).content || "",
            (item || {}).comment || ""
        ].join(" ").toLowerCase();
        return haystack.indexOf(needle) >= 0;
    }

    function worldbookEntryMatchesFilter(item, index) {
        const groupOk = worldbookGroupFilter === "__all__" || worldbookGroupKey(item) === worldbookGroupFilter;
        return groupOk && worldbookEntryMatchesSearch(item, index);
    }

    function filteredWorldbookEntries() {
        const result = [];
        for (let i = 0; i < worldbookEntries.length; ++i) {
            const item = worldbookEntries[i] || {};
            if (worldbookEntryMatchesFilter(item, i)) {
                result.push({ "sourceIndex": i, "item": item });
            }
        }
        return result;
    }

    function visibleWorldbookPickerEntries() {
        const result = filteredWorldbookEntries();
        if (worldbookEntryPickerExpanded || result.length <= 24) {
            return result;
        }
        return result.slice(0, 24);
    }

    function worldbookFilterSummaryText() {
        const filteredCount = filteredWorldbookEntries().length;
        const visibleCount = visibleWorldbookPickerEntries().length;
        const groupLabel = worldbookGroupLabel(worldbookGroupFilter);
        const search = String(worldbookSearchText || "").trim();
        let text = `当前筛选：${groupLabel} · ${filteredCount}/${worldbookEntries.length} 条`;
        if (search.length > 0) {
            text += ` · 搜索“${search}”`;
        }
        if (visibleCount < filteredCount) {
            text += ` · 已显示前 ${visibleCount} 条`;
        }
        return text;
    }

    function worldbookEntryPickerLabel(modelItem) {
        const sourceIndex = Number((modelItem || {}).sourceIndex || 0);
        const item = (modelItem || {}).item || {};
        const group = worldbookGroupLabel(worldbookGroupKey(item));
        const title = worldbookTitle(item, sourceIndex);
        return group === "未分组" ? title : `${title} · ${group}`;
    }

    function presetItemTitle(item, index) {
        return item.name || item.id || `提示 ${index + 1}`;
    }

    function presetGroupTitle(item, index) {
        return item.name || item.id || `预设组 ${index + 1}`;
    }

    function presetGroupItemTitle(item, index) {
        return item.name || item.id || `组内提示 ${index + 1}`;
    }

    function currentPresetItemTitle(item, index) {
        return selectedPresetCollection === "prompt_groups"
            ? presetGroupTitle(item, index)
            : presetItemTitle(item, index);
    }

    function memoryTitle(item, index) {
        return item.title || item.content || `记忆 ${index + 1}`;
    }

    function personaTitle(item, index) {
        return item.name || item.id || `多角色 ${index + 1}`;
    }

    function workshopTitle(item, index) {
        return item.name || item.id || `Workshop ${index + 1}`;
    }

    function personaMapToItems(personas) {
        const result = [];
        const source = personas || {};
        const keys = Object.keys(source);
        keys.sort(function (a, b) {
            const an = Number(a);
            const bn = Number(b);
            if (!isNaN(an) && !isNaN(bn)) {
                return an - bn;
            }
            return String(a).localeCompare(String(b));
        });
        for (let i = 0; i < keys.length; ++i) {
            const key = keys[i];
            const item = clone(source[key] || {});
            item.id = item.id || key;
            item._key = key;
            result.push(item);
        }
        return result;
    }

    function personaItemsToMap(items) {
        const result = {};
        const used = {};
        for (let i = 0; i < (items || []).length; ++i) {
            const item = items[i] || {};
            let key = String(item.id || item._key || (i + 1)).trim();
            if (key.length === 0) {
                key = String(i + 1);
            }
            const baseKey = key;
            let suffix = 2;
            while (used[key]) {
                key = `${baseKey}_${suffix}`;
                suffix += 1;
            }
            used[key] = true;
            const value = clone(item);
            delete value.id;
            delete value._key;
            value.name = item.name || "";
            value.description = item.description || "";
            value.personality = item.personality || "";
            value.scenario = item.scenario || "";
            value.creator_notes = item.creator_notes || "";
            value.tags = clone(item.tags || []);
            result[key] = value;
        }
        return result;
    }

    function applyPersonaFields(item) {
        item = item || {};
        personaIdText = item.id || item._key || "";
        personaNameText = item.name || "";
        personaDescriptionText = item.description || "";
        personaPersonalityText = item.personality || "";
        personaScenarioText = item.scenario || "";
        personaCreatorNotesText = item.creator_notes || "";
        personaTagsText = tagsToText(item.tags || []);
    }

    function applyWorkshopFields(item) {
        item = item || {};
        workshopIdText = item.id || "";
        workshopNameText = item.name || "";
        workshopEnabled = item.enabled === undefined ? true : Boolean(item.enabled);
        workshopTriggerModeText = item.triggerMode || "manual";
        workshopTriggerStageText = item.triggerStage || "";
        workshopTriggerTempMinText = String(item.triggerTempMin === undefined ? 0 : item.triggerTempMin);
        workshopTriggerTempMaxText = String(item.triggerTempMax === undefined ? 1 : item.triggerTempMax);
        workshopActionTypeText = item.actionType || "note";
        workshopPopupTitleText = item.popupTitle || "";
        workshopMusicPresetText = item.musicPreset || "";
        workshopMusicUrlText = item.musicUrl || "";
        workshopAutoplay = item.autoplay === undefined ? false : Boolean(item.autoplay);
        workshopLoop = item.loop === undefined ? false : Boolean(item.loop);
        workshopVolumeText = String(item.volume === undefined ? 0.7 : item.volume);
        workshopImageUrlText = item.imageUrl || "";
        workshopImageAltText = item.imageAlt || "";
        workshopNoteText = item.note || "";
    }

    function applyVariableFields(item) {
        item = item || {};
        variableKeyText = item.key || "";
        variableLabelText = item.label || "";
        variableTypeText = item.value_type || "text";
        variableScopeText = item.scope || "role";
        variableInitialValueText = item.initial_value || "";
        variableDescriptionText = item.description || "";
        variableWritePolicyText = item.write_policy || "";
        variableNotesText = item.notes || "";
    }

    function applyStageFields(item) {
        item = item || {};
        stageRoleText = item.role_id || "role";
        stageKeyText = item.stage_key || "";
        stageTitleText = item.title || "";
        stageConditionText = item.condition || "";
        stageActiveTagText = item.active_tag || "";
        stageEmitsTagsText = tagsToText(item.emits_tags || []);
        stageDescriptionText = item.description || "";
        stageNotesText = item.notes || "";
    }

    function applySnapshotFieldFields(item) {
        item = item || {};
        snapshotRoleText = item.role_id || "role";
        snapshotKeyText = item.key || "";
        snapshotLabelText = item.label || "";
        snapshotEnabled = item.enabled === undefined ? true : Boolean(item.enabled);
        snapshotDisplay = item.display === undefined ? true : Boolean(item.display);
        snapshotInstructionText = item.instruction || "";
        snapshotNotesText = item.notes || "";
    }

    function applyDatabaseTagFields(item) {
        item = item || {};
        databaseTagText = item.tag || "";
        databaseTagTitleText = item.title || "";
        databaseTagTriggerText = item.trigger || "";
        databaseTagTargetText = item.target || "worldbook";
        databaseTagDescriptionText = item.description || "";
        databaseTagNotesText = item.notes || "";
    }

    function applyWorldbookFields(item) {
        item = item || {};
        worldbookIdText = item.id || "";
        worldbookTitleText = item.title || "";
        worldbookTriggerText = item.trigger || "";
        worldbookSecondaryTriggerText = item.secondary_trigger || "";
        worldbookEntryTypeText = item.entry_type || "keyword";
        worldbookGroupText = item.group || "";
        worldbookGroupOperatorText = item.group_operator || "and";
        worldbookMatchModeText = item.match_mode || "any";
        worldbookSecondaryModeText = item.secondary_mode || "all";
        worldbookContentText = item.content || "";
        worldbookCommentText = item.comment || "";
        worldbookOrderText = String(item.order === undefined ? 100 : item.order);
        worldbookChanceText = String(item.chance === undefined ? 100 : item.chance);
        worldbookStickyTurnsText = String(item.sticky_turns === undefined ? 0 : item.sticky_turns);
        worldbookCooldownTurnsText = String(item.cooldown_turns === undefined ? 0 : item.cooldown_turns);
        worldbookInsertionPositionText = item.insertion_position || "after_char_defs";
        worldbookInjectionDepthText = String(item.injection_depth === undefined ? 0 : item.injection_depth);
        worldbookInjectionRoleText = item.injection_role || "system";
        worldbookInjectionOrderText = String(item.injection_order === undefined ? 100 : item.injection_order);
        worldbookPromptLayerText = item.prompt_layer || "follow_position";
        worldbookExternalSourceText = item.external_source || "";
        worldbookActivationTagsText = tagsToText(item.activation_tags || []);
        worldbookEnabled = item.enabled === undefined ? true : Boolean(item.enabled);
        worldbookRecursiveEnabled = item.recursive_enabled === undefined ? true : Boolean(item.recursive_enabled);
        worldbookPreventFurtherRecursion = item.prevent_further_recursion === undefined ? false : Boolean(item.prevent_further_recursion);
        worldbookCaseSensitive = item.case_sensitive === undefined ? false : Boolean(item.case_sensitive);
        worldbookWholeWord = item.whole_word === undefined ? false : Boolean(item.whole_word);
    }

    function applyPresetItemFields(item) {
        item = item || {};
        if (selectedPresetCollection === "prompt_groups") {
            presetGroupIdText = item.id || "";
            presetGroupNameText = item.name || "";
            presetGroupEnabled = item.enabled === undefined ? true : Boolean(item.enabled);
            presetGroupSelectionModeText = item.selection_mode || "single";
            presetGroupSelectedIdsText = tagsToText(item.selected_ids || []);
            presetGroupOrderText = String(item.order === undefined ? 100 : item.order);
            selectPresetGroupItem((item.items || []).length > 0 ? 0 : -1);
            return;
        }
        presetItemIdText = item.id || "";
        presetItemNameText = item.name || "";
        presetItemContentText = item.content || "";
        presetItemOrderText = String(item.order === undefined ? 100 : item.order);
        presetItemPlacementText = item.placement || "";
        presetItemKindText = item.kind || "";
        presetItemStrengthText = item.strength || "";
        presetItemRoleText = item.role || "system";
        presetItemDepthText = String(item.depth === undefined ? 0 : item.depth);
        presetItemTokenBudgetText = item.tokenBudget === undefined ? "" : String(item.tokenBudget);
        presetItemActivationTagsText = tagsToText(item.activation_tags || []);
        presetItemEnabled = item.enabled === undefined ? true : Boolean(item.enabled);
        presetItemRequired = item.required === undefined ? false : Boolean(item.required);
        selectPresetGroupItem(-1);
    }

    function applyPresetGroupItemFields(item) {
        item = item || {};
        presetGroupItemIdText = item.id || "";
        presetGroupItemNameText = item.name || "";
        presetGroupItemContentText = item.content || "";
        presetGroupItemPlacementText = item.placement || "";
        presetGroupItemKindText = item.kind || "";
        presetGroupItemStrengthText = item.strength || "";
        presetGroupItemRoleText = item.role || "system";
        presetGroupItemDepthText = String(item.depth === undefined ? 0 : item.depth);
        presetGroupItemTokenBudgetText = item.tokenBudget === undefined ? "" : String(item.tokenBudget);
        presetGroupItemActivationTagsText = tagsToText(item.activation_tags || []);
        presetGroupItemEnabled = item.enabled === undefined ? true : Boolean(item.enabled);
        presetGroupItemRequired = item.required === undefined ? false : Boolean(item.required);
    }

    function applyMemoryFields(item) {
        item = item || {};
        memoryIdText = item.id || "";
        memoryTitleText = item.title || "";
        memoryContentText = item.content || "";
        memoryTagsText = tagsToText(item.tags || []);
        memoryNotesText = item.notes || "";
        memoryStatusText = item.memory_status || item.status || "active";
    }

    function selectVariable(index) {
        selectedVariableIndex = index >= 0 && index < databaseVariables.length ? index : -1;
        applyVariableFields(selectedVariableIndex >= 0 ? databaseVariables[selectedVariableIndex] : {});
    }

    function selectStage(index) {
        selectedStageIndex = index >= 0 && index < databaseStages.length ? index : -1;
        applyStageFields(selectedStageIndex >= 0 ? databaseStages[selectedStageIndex] : {});
    }

    function selectSnapshotField(index) {
        selectedSnapshotFieldIndex = index >= 0 && index < databaseSnapshotFields.length ? index : -1;
        applySnapshotFieldFields(selectedSnapshotFieldIndex >= 0 ? databaseSnapshotFields[selectedSnapshotFieldIndex] : {});
    }

    function selectDatabaseTag(index) {
        selectedTagIndex = index >= 0 && index < databaseTags.length ? index : -1;
        applyDatabaseTagFields(selectedTagIndex >= 0 ? databaseTags[selectedTagIndex] : {});
    }

    function selectWorldbookEntry(index) {
        selectedWorldbookIndex = index >= 0 && index < worldbookEntries.length ? index : -1;
        applyWorldbookFields(selectedWorldbookIndex >= 0 ? worldbookEntries[selectedWorldbookIndex] : {});
    }

    function currentPresetItems() {
        return selectedPresetCollection === "prompt_groups" ? presetPromptGroups : presetExtraPrompts;
    }

    function currentPresetGroupItems() {
        if (selectedPresetCollection !== "prompt_groups") {
            return [];
        }
        const groups = currentPresetItems();
        if (selectedPresetItemIndex < 0 || selectedPresetItemIndex >= groups.length) {
            return [];
        }
        return (groups[selectedPresetItemIndex] || {}).items || [];
    }

    function setCurrentPresetItems(items) {
        if (selectedPresetCollection === "prompt_groups") {
            presetPromptGroups = items;
        } else {
            presetExtraPrompts = items;
        }
    }

    function selectPresetCollection(collection) {
        selectedPresetCollection = collection === "prompt_groups" ? "prompt_groups" : "extra_prompts";
        selectPresetItem(currentPresetItems().length > 0 ? 0 : -1);
    }

    function selectPresetItem(index) {
        const items = currentPresetItems();
        selectedPresetItemIndex = index >= 0 && index < items.length ? index : -1;
        applyPresetItemFields(selectedPresetItemIndex >= 0 ? items[selectedPresetItemIndex] : {});
    }

    function selectPresetGroupItem(index) {
        const items = currentPresetGroupItems();
        selectedPresetGroupItemIndex = index >= 0 && index < items.length ? index : -1;
        applyPresetGroupItemFields(selectedPresetGroupItemIndex >= 0 ? items[selectedPresetGroupItemIndex] : {});
    }

    function selectMemoryItem(index) {
        selectedMemoryIndex = index >= 0 && index < memoryItems.length ? index : -1;
        applyMemoryFields(selectedMemoryIndex >= 0 ? memoryItems[selectedMemoryIndex] : {});
    }

    function selectPersonaItem(index) {
        selectedPersonaIndex = index >= 0 && index < personaItems.length ? index : -1;
        applyPersonaFields(selectedPersonaIndex >= 0 ? personaItems[selectedPersonaIndex] : {});
    }

    function selectWorkshopItem(index) {
        selectedWorkshopIndex = index >= 0 && index < workshopItems.length ? index : -1;
        applyWorkshopFields(selectedWorkshopIndex >= 0 ? workshopItems[selectedWorkshopIndex] : {});
    }

    function updateVariableField(field, value) {
        if (selectedVariableIndex < 0 || selectedVariableIndex >= databaseVariables.length) {
            return;
        }
        const items = clone(databaseVariables);
        items[selectedVariableIndex] = items[selectedVariableIndex] || defaultVariable(selectedVariableIndex);
        items[selectedVariableIndex][field] = value;
        databaseVariables = items;
        markDirty();
    }

    function updateStageField(field, value) {
        if (selectedStageIndex < 0 || selectedStageIndex >= databaseStages.length) {
            return;
        }
        const items = clone(databaseStages);
        items[selectedStageIndex] = items[selectedStageIndex] || defaultStage(selectedStageIndex);
        items[selectedStageIndex][field] = value;
        databaseStages = items;
        markDirty();
    }

    function updateSnapshotField(field, value) {
        if (selectedSnapshotFieldIndex < 0 || selectedSnapshotFieldIndex >= databaseSnapshotFields.length) {
            return;
        }
        const items = clone(databaseSnapshotFields);
        items[selectedSnapshotFieldIndex] = items[selectedSnapshotFieldIndex] || defaultSnapshotField(selectedSnapshotFieldIndex);
        items[selectedSnapshotFieldIndex][field] = value;
        databaseSnapshotFields = items;
        markDirty();
    }

    function updateDatabaseTagField(field, value) {
        if (selectedTagIndex < 0 || selectedTagIndex >= databaseTags.length) {
            return;
        }
        const items = clone(databaseTags);
        items[selectedTagIndex] = items[selectedTagIndex] || defaultDatabaseTag(selectedTagIndex);
        items[selectedTagIndex][field] = value;
        databaseTags = items;
        markDirty();
    }

    function updateWorldbookField(field, value) {
        if (selectedWorldbookIndex < 0 || selectedWorldbookIndex >= worldbookEntries.length) {
            return;
        }
        const items = clone(worldbookEntries);
        items[selectedWorldbookIndex] = items[selectedWorldbookIndex] || defaultWorldbookEntry(selectedWorldbookIndex);
        if (field === "order" || field === "priority" || field === "chance" || field === "sticky_turns" || field === "cooldown_turns" || field === "injection_depth" || field === "injection_order") {
            items[selectedWorldbookIndex][field] = numericOrDefault(value, 0);
        } else if (field === "activation_tags") {
            items[selectedWorldbookIndex][field] = splitTagsText(value);
        } else {
            items[selectedWorldbookIndex][field] = value;
        }
        worldbookEntries = items;
        markDirty();
    }

    function updateWorldbookSetting(field, value) {
        const settings = clone(worldbookSettings || {});
        if (field === "max_hits" || field === "default_chance" || field === "default_sticky_turns" || field === "default_cooldown_turns" || field === "default_injection_depth" || field === "default_injection_order" || field === "recursion_max_depth") {
            settings[field] = numericOrDefault(value, 0);
        } else {
            settings[field] = value;
        }
        worldbookSettings = settings;
        markDirty();
    }

    function updatePresetModule(key, value) {
        const modules = clone(presetModules || {});
        modules[key] = Boolean(value);
        presetModules = modules;
        markDirty();
    }

    function updatePresetItemField(field, value) {
        const items = clone(currentPresetItems());
        if (selectedPresetItemIndex < 0 || selectedPresetItemIndex >= items.length) {
            return;
        }
        items[selectedPresetItemIndex] = items[selectedPresetItemIndex] || defaultPresetItem(selectedPresetItemIndex, selectedPresetCollection);
        if (field === "order" || field === "depth" || field === "tokenBudget") {
            items[selectedPresetItemIndex][field] = numericOrDefault(value, 0);
        } else if (field === "activation_tags" || field === "selected_ids") {
            items[selectedPresetItemIndex][field] = splitTagsText(value);
        } else {
            items[selectedPresetItemIndex][field] = value;
        }
        setCurrentPresetItems(items);
        markDirty();
    }

    function updatePresetGroupItemField(field, value) {
        if (selectedPresetCollection !== "prompt_groups") {
            return;
        }
        const groups = clone(presetPromptGroups);
        if (selectedPresetItemIndex < 0 || selectedPresetItemIndex >= groups.length) {
            return;
        }
        groups[selectedPresetItemIndex] = groups[selectedPresetItemIndex] || defaultPresetItem(selectedPresetItemIndex, "prompt_groups");
        const groupItems = groups[selectedPresetItemIndex].items || [];
        if (selectedPresetGroupItemIndex < 0 || selectedPresetGroupItemIndex >= groupItems.length) {
            return;
        }
        groupItems[selectedPresetGroupItemIndex] = groupItems[selectedPresetGroupItemIndex] || defaultPresetGroupItem(selectedPresetGroupItemIndex);
        if (field === "depth" || field === "tokenBudget") {
            groupItems[selectedPresetGroupItemIndex][field] = numericOrDefault(value, 0);
        } else if (field === "activation_tags") {
            groupItems[selectedPresetGroupItemIndex][field] = splitTagsText(value);
        } else {
            groupItems[selectedPresetGroupItemIndex][field] = value;
        }
        groups[selectedPresetItemIndex].items = groupItems;
        presetPromptGroups = groups;
        markDirty();
    }

    function togglePresetGroupSelectedId(itemId, checked) {
        if (selectedPresetCollection !== "prompt_groups" || !itemId) {
            return;
        }
        const groups = clone(presetPromptGroups);
        if (selectedPresetItemIndex < 0 || selectedPresetItemIndex >= groups.length) {
            return;
        }
        groups[selectedPresetItemIndex] = groups[selectedPresetItemIndex] || defaultPresetItem(selectedPresetItemIndex, "prompt_groups");
        const selected = groups[selectedPresetItemIndex].selected_ids || [];
        const index = selected.indexOf(itemId);
        if (checked && index < 0) {
            if ((groups[selectedPresetItemIndex].selection_mode || "single") === "single") {
                groups[selectedPresetItemIndex].selected_ids = [itemId];
            } else {
                selected.push(itemId);
                groups[selectedPresetItemIndex].selected_ids = selected;
            }
        } else if (!checked && index >= 0) {
            selected.splice(index, 1);
            groups[selectedPresetItemIndex].selected_ids = selected;
        }
        presetPromptGroups = groups;
        presetGroupSelectedIdsText = tagsToText((groups[selectedPresetItemIndex] || {}).selected_ids || []);
        markDirty();
    }

    function updateMemoryField(field, value) {
        if (selectedMemoryIndex < 0 || selectedMemoryIndex >= memoryItems.length) {
            return;
        }
        const items = clone(memoryItems);
        items[selectedMemoryIndex] = items[selectedMemoryIndex] || defaultMemoryItem(selectedMemoryIndex);
        items[selectedMemoryIndex][field] = value;
        memoryItems = items;
        markDirty();
    }

    function updatePersonaField(field, value) {
        if (selectedPersonaIndex < 0 || selectedPersonaIndex >= personaItems.length) {
            return;
        }
        const items = clone(personaItems);
        items[selectedPersonaIndex] = items[selectedPersonaIndex] || defaultPersonaItem(selectedPersonaIndex);
        items[selectedPersonaIndex][field] = value;
        personaItems = items;
        markDirty();
    }

    function updateWorkshopField(field, value) {
        if (selectedWorkshopIndex < 0 || selectedWorkshopIndex >= workshopItems.length) {
            return;
        }
        const items = clone(workshopItems);
        items[selectedWorkshopIndex] = items[selectedWorkshopIndex] || defaultWorkshopItem(selectedWorkshopIndex);
        if (field === "triggerTempMin" || field === "triggerTempMax") {
            const numericValue = Number(value);
            items[selectedWorkshopIndex][field] = isNaN(numericValue) ? 0 : Math.trunc(numericValue);
        } else if (field === "volume") {
            const numericValue = Number(value);
            items[selectedWorkshopIndex][field] = isNaN(numericValue) ? 0.7 : numericValue;
        } else {
            items[selectedWorkshopIndex][field] = value;
        }
        workshopItems = items;
        creativeWorkshopPresent = true;
        markDirty();
    }

    function addVariable() {
        const items = clone(databaseVariables);
        items.push(defaultVariable(items.length));
        databaseVariables = items;
        selectVariable(items.length - 1);
        markDirty();
    }

    function addStage() {
        const items = clone(databaseStages);
        items.push(defaultStage(items.length));
        databaseStages = items;
        selectStage(items.length - 1);
        markDirty();
    }

    function addSnapshotField() {
        const items = clone(databaseSnapshotFields);
        items.push(defaultSnapshotField(items.length));
        databaseSnapshotFields = items;
        selectSnapshotField(items.length - 1);
        markDirty();
    }

    function addDatabaseTag() {
        const items = clone(databaseTags);
        items.push(defaultDatabaseTag(items.length));
        databaseTags = items;
        selectDatabaseTag(items.length - 1);
        markDirty();
    }

    function addWorldbookEntry() {
        const items = clone(worldbookEntries);
        items.push(defaultWorldbookEntry(items.length));
        worldbookEntries = items;
        worldbookGroupFilter = "__all__";
        worldbookSearchText = "";
        worldbookEntryPickerExpanded = true;
        selectWorldbookEntry(items.length - 1);
        markDirty();
    }

    function addPresetItem() {
        const items = clone(currentPresetItems());
        items.push(defaultPresetItem(items.length, selectedPresetCollection));
        setCurrentPresetItems(items);
        selectPresetItem(items.length - 1);
        markDirty();
    }

    function addPresetGroupItem() {
        if (selectedPresetCollection !== "prompt_groups" || selectedPresetItemIndex < 0) {
            return;
        }
        const groups = clone(presetPromptGroups);
        groups[selectedPresetItemIndex] = groups[selectedPresetItemIndex] || defaultPresetItem(selectedPresetItemIndex, "prompt_groups");
        const items = groups[selectedPresetItemIndex].items || [];
        items.push(defaultPresetGroupItem(items.length));
        groups[selectedPresetItemIndex].items = items;
        presetPromptGroups = groups;
        selectPresetGroupItem(items.length - 1);
        markDirty();
    }

    function addMemoryItem() {
        const items = clone(memoryItems);
        items.push(defaultMemoryItem(items.length));
        memoryItems = items;
        selectMemoryItem(items.length - 1);
        markDirty();
    }

    function addPersonaItem() {
        const items = clone(personaItems);
        items.push(defaultPersonaItem(items.length));
        personaItems = items;
        selectPersonaItem(items.length - 1);
        markDirty();
    }

    function addWorkshopItem() {
        const items = clone(workshopItems);
        items.push(defaultWorkshopItem(items.length));
        workshopItems = items;
        creativeWorkshopPresent = true;
        selectWorkshopItem(items.length - 1);
        markDirty();
    }

    function removeVariable() {
        if (selectedVariableIndex < 0 || selectedVariableIndex >= databaseVariables.length) {
            return;
        }
        const items = clone(databaseVariables);
        items.splice(selectedVariableIndex, 1);
        databaseVariables = items;
        selectVariable(Math.min(selectedVariableIndex, items.length - 1));
        markDirty();
    }

    function removeStage() {
        if (selectedStageIndex < 0 || selectedStageIndex >= databaseStages.length) {
            return;
        }
        const items = clone(databaseStages);
        items.splice(selectedStageIndex, 1);
        databaseStages = items;
        selectStage(Math.min(selectedStageIndex, items.length - 1));
        markDirty();
    }

    function removeSnapshotField() {
        if (selectedSnapshotFieldIndex < 0 || selectedSnapshotFieldIndex >= databaseSnapshotFields.length) {
            return;
        }
        const items = clone(databaseSnapshotFields);
        items.splice(selectedSnapshotFieldIndex, 1);
        databaseSnapshotFields = items;
        selectSnapshotField(Math.min(selectedSnapshotFieldIndex, items.length - 1));
        markDirty();
    }

    function removeDatabaseTag() {
        if (selectedTagIndex < 0 || selectedTagIndex >= databaseTags.length) {
            return;
        }
        const items = clone(databaseTags);
        items.splice(selectedTagIndex, 1);
        databaseTags = items;
        selectDatabaseTag(Math.min(selectedTagIndex, items.length - 1));
        markDirty();
    }

    function removeWorldbookEntry() {
        if (selectedWorldbookIndex < 0 || selectedWorldbookIndex >= worldbookEntries.length) {
            return;
        }
        const items = clone(worldbookEntries);
        items.splice(selectedWorldbookIndex, 1);
        worldbookEntries = items;
        selectWorldbookEntry(Math.min(selectedWorldbookIndex, items.length - 1));
        markDirty();
    }

    function removePresetItem() {
        const items = clone(currentPresetItems());
        if (selectedPresetItemIndex < 0 || selectedPresetItemIndex >= items.length) {
            return;
        }
        items.splice(selectedPresetItemIndex, 1);
        setCurrentPresetItems(items);
        selectPresetItem(Math.min(selectedPresetItemIndex, items.length - 1));
        markDirty();
    }

    function removePresetGroupItem() {
        if (selectedPresetCollection !== "prompt_groups") {
            return;
        }
        const groups = clone(presetPromptGroups);
        if (selectedPresetItemIndex < 0 || selectedPresetItemIndex >= groups.length) {
            return;
        }
        const items = groups[selectedPresetItemIndex].items || [];
        if (selectedPresetGroupItemIndex < 0 || selectedPresetGroupItemIndex >= items.length) {
            return;
        }
        const removedId = (items[selectedPresetGroupItemIndex] || {}).id || "";
        items.splice(selectedPresetGroupItemIndex, 1);
        groups[selectedPresetItemIndex].items = items;
        if (removedId) {
            const selected = groups[selectedPresetItemIndex].selected_ids || [];
            groups[selectedPresetItemIndex].selected_ids = selected.filter(function (id) { return id !== removedId; });
        }
        presetPromptGroups = groups;
        selectPresetGroupItem(Math.min(selectedPresetGroupItemIndex, items.length - 1));
        markDirty();
    }

    function removeMemoryItem() {
        if (selectedMemoryIndex < 0 || selectedMemoryIndex >= memoryItems.length) {
            return;
        }
        const items = clone(memoryItems);
        items.splice(selectedMemoryIndex, 1);
        memoryItems = items;
        selectMemoryItem(Math.min(selectedMemoryIndex, items.length - 1));
        markDirty();
    }

    function removePersonaItem() {
        if (selectedPersonaIndex < 0 || selectedPersonaIndex >= personaItems.length) {
            return;
        }
        const items = clone(personaItems);
        items.splice(selectedPersonaIndex, 1);
        personaItems = items;
        selectPersonaItem(Math.min(selectedPersonaIndex, items.length - 1));
        markDirty();
    }

    function removeWorkshopItem() {
        if (selectedWorkshopIndex < 0 || selectedWorkshopIndex >= workshopItems.length) {
            return;
        }
        const items = clone(workshopItems);
        items.splice(selectedWorkshopIndex, 1);
        workshopItems = items;
        creativeWorkshopPresent = true;
        selectWorkshopItem(Math.min(selectedWorkshopIndex, items.length - 1));
        markDirty();
    }

    function activePresetFromProject(preset) {
        preset = preset || {};
        const presets = preset.presets || [];
        if (!presets || presets.length === 0) {
            return preset;
        }
        const activeId = preset.active_preset_id || "";
        for (let i = 0; i < presets.length; ++i) {
            if ((presets[i] || {}).id === activeId) {
                return presets[i] || {};
            }
        }
        return presets[0] || {};
    }

    function writePresetToProject(project, activePreset) {
        project.preset = project.preset || {};
        const presets = project.preset.presets || [];
        if (presets && presets.length > 0) {
            let targetIndex = 0;
            const activeId = project.preset.active_preset_id || activePreset.id || "";
            for (let i = 0; i < presets.length; ++i) {
                if ((presets[i] || {}).id === activeId) {
                    targetIndex = i;
                    break;
                }
            }
            const nextPresets = clone(presets);
            nextPresets[targetIndex] = Object.assign({}, nextPresets[targetIndex] || {}, activePreset);
            project.preset.presets = nextPresets;
            project.preset.active_preset_id = nextPresets[targetIndex].id || activeId;
        } else {
            project.preset = Object.assign({}, project.preset, activePreset);
            project.preset.active_preset_id = project.preset.active_preset_id || activePreset.id || presetActivePresetId;
        }
    }

    function applyDraft(draft) {
        initialized = false;
        projectDraft = clone(draft || {});
        refreshProjectItems();
        const persona = projectDraft.persona_card || {};
        const database = projectDraft.database || {};
        const worldbook = projectDraft.worldbook || {};
        const preset = projectDraft.preset || {};
        const activePreset = activePresetFromProject(preset);
        const memory = projectDraft.memory || {};
        titleText = projectDraft.title || "";
        cardNameText = persona.name || "";
        tagsText = tagsToText(persona.tags || []);
        descriptionText = persona.description || "";
        personalityText = persona.personality || "";
        scenarioText = persona.scenario || "";
        firstMessageText = persona.first_mes || "";
        mesExampleText = persona.mes_example || "";
        creatorNotesText = persona.creator_notes || "";
        personaItems = personaMapToItems(persona.personas || {});
        creativeWorkshopPresent = Object.prototype.hasOwnProperty.call(persona, "creativeWorkshop");
        const creativeWorkshop = persona.creativeWorkshop || {};
        creativeWorkshopDraft = clone(creativeWorkshop);
        creativeWorkshopEnabled = creativeWorkshop.enabled === undefined ? true : Boolean(creativeWorkshop.enabled);
        workshopItems = clone(creativeWorkshop.items || []);
        databaseEnabled = database.enabled === undefined ? true : Boolean(database.enabled);
        databaseNotesText = database.notes || "";
        databaseVariables = clone(database.variables || []);
        databaseStages = clone(database.stages || []);
        databaseSnapshotFields = clone(database.snapshotFields || database.snapshot_fields || []);
        databaseTags = clone(database.tags || []);
        worldbookSettings = clone(worldbook.settings || {});
        worldbookEntries = clone(worldbook.entries || worldbook.items || []);
        worldbookGroupFilter = "__all__";
        worldbookSearchText = "";
        worldbookEntryPickerExpanded = false;
        presetActivePresetId = preset.active_preset_id || activePreset.id || "";
        presetNameText = activePreset.name || "";
        presetEnabled = activePreset.enabled === undefined ? true : Boolean(activePreset.enabled);
        presetBaseSystemPromptText = activePreset.base_system_prompt || "";
        presetModules = clone(activePreset.modules || {});
        presetExtraPrompts = clone(activePreset.extra_prompts || []);
        presetPromptGroups = clone(activePreset.prompt_groups || []);
        selectedPresetCollection = "extra_prompts";
        memoryItems = clone(memory.items || memory.entries || memory.memories || []);
        selectVariable(databaseVariables.length > 0 ? 0 : -1);
        selectStage(databaseStages.length > 0 ? 0 : -1);
        selectSnapshotField(databaseSnapshotFields.length > 0 ? 0 : -1);
        selectDatabaseTag(databaseTags.length > 0 ? 0 : -1);
        selectWorldbookEntry(worldbookEntries.length > 0 ? 0 : -1);
        selectPresetItem(presetExtraPrompts.length > 0 ? 0 : -1);
        selectMemoryItem(memoryItems.length > 0 ? 0 : -1);
        selectPersonaItem(personaItems.length > 0 ? 0 : -1);
        selectWorkshopItem(workshopItems.length > 0 ? 0 : -1);
        previewResult = clone(FantarealBridge.cardAuthoringPreview || {});
        previewGroups = previewResult.groups || [];
        previewWarnings = previewResult.warnings || [];
        previewStale = previewGroups.length > 0 || Boolean((previewResult || {}).ok);
        previewDraftKey = "";
        previewModuleKey = "";
        compiledResult = ({});
        compiledWarnings = [];
        pendingApplyDraft = ({});
        pendingApplyGroups = [];
        pendingApplyPreview = ({});
        lastOperationResult = ({});
        dirty = false;
        initialized = true;
    }

    function buildDraft() {
        const project = clone(projectDraft);
        project.type = project.type || "fantareal_card_authoring_project";
        project.version = project.version || 1;
        project.title = titleText;
        project.persona_card = project.persona_card || {};
        project.persona_card.name = cardNameText;
        project.persona_card.tags = splitTagsText(tagsText);
        project.persona_card.description = descriptionText;
        project.persona_card.personality = personalityText;
        project.persona_card.scenario = scenarioText;
        project.persona_card.first_mes = firstMessageText;
        project.persona_card.mes_example = mesExampleText;
        project.persona_card.creator_notes = creatorNotesText;
        project.persona_card.personas = personaItemsToMap(personaItems);
        if (creativeWorkshopPresent || workshopItems.length > 0 || !creativeWorkshopEnabled) {
            const creativeWorkshop = clone(creativeWorkshopDraft || {});
            creativeWorkshop.enabled = creativeWorkshopEnabled;
            creativeWorkshop.items = clone(workshopItems);
            project.persona_card.creativeWorkshop = creativeWorkshop;
        } else {
            delete project.persona_card.creativeWorkshop;
        }
        project.database = project.database || {};
        project.database.enabled = databaseEnabled;
        project.database.notes = databaseNotesText;
        project.database.variables = clone(databaseVariables);
        project.database.stages = clone(databaseStages);
        project.database.snapshotFields = clone(databaseSnapshotFields);
        project.database.tags = clone(databaseTags);
        project.worldbook = project.worldbook || {};
        project.worldbook.settings = clone(worldbookSettings || {});
        project.worldbook.entries = clone(worldbookEntries);
        writePresetToProject(project, {
            "id": presetActivePresetId || "card-authoring-preset",
            "name": presetNameText || "写卡器预设",
            "enabled": presetEnabled,
            "base_system_prompt": presetBaseSystemPromptText,
            "modules": clone(presetModules || {}),
            "extra_prompts": clone(presetExtraPrompts),
            "prompt_groups": clone(presetPromptGroups)
        });
        project.memory = project.memory || {};
        project.memory.items = clone(memoryItems);
        return project;
    }

    function selectedGroupIds() {
        const groups = [];
        if (applyPersona) {
            groups.push("persona");
        }
        if (applyDatabase) {
            groups.push("database");
        }
        if (applyWorldbook) {
            groups.push("worldbook");
        }
        if (applyPreset) {
            groups.push("preset");
        }
        if (applyMemory) {
            groups.push("memory");
        }
        return groups;
    }

    function moduleLabel(moduleId) {
        if (moduleId === "persona") {
            return "主卡";
        }
        if (moduleId === "database") {
            return "数据库";
        }
        if (moduleId === "worldbook") {
            return "世界书";
        }
        if (moduleId === "preset") {
            return "预设";
        }
        if (moduleId === "memory") {
            return "记忆";
        }
        return moduleId || "";
    }

    function moduleLabels(moduleIds) {
        const labels = [];
        const items = moduleIds || [];
        for (let i = 0; i < items.length; ++i) {
            const label = moduleLabel(items[i]);
            if (label.length > 0) {
                labels.push(label);
            }
        }
        return labels;
    }

    function moduleKey(groups) {
        const items = clone(groups || []);
        items.sort();
        return items.join("|");
    }

    function draftKey(draft) {
        try {
            return JSON.stringify(draft || {});
        } catch (error) {
            return "";
        }
    }

    function previewMatchesCurrent() {
        const groups = selectedGroupIds();
        if (groups.length === 0 || previewStale || !(previewResult || {}).ok) {
            return false;
        }
        return previewDraftKey.length > 0 && previewDraftKey === draftKey(buildDraft()) && previewModuleKey === moduleKey(groups);
    }

    function backupList(result) {
        const backups = clone((result || {}).backups || []);
        const backupPath = (result || {}).backupPath || "";
        if (backupPath.length > 0 && backups.indexOf(backupPath) < 0) {
            backups.push(backupPath);
        }
        return backups;
    }

    function applyResultSummary(result) {
        result = result || {};
        const applied = clone(result.applied || []);
        const backups = backupList(result);
        const modules = moduleLabels(applied.length > 0 ? applied : pendingApplyGroups);
        return {
            "ok": Boolean(result.ok),
            "message": result.message || "",
            "applied": applied,
            "backups": backups,
            "moduleText": modules.join("、"),
            "appliedCount": applied.length,
            "backupCount": backups.length,
            "timeText": new Date().toLocaleString()
        };
    }

    function candidateById(candidateId) {
        for (let i = 0; i < candidateCandidates.length; ++i) {
            const candidate = candidateCandidates[i] || {};
            if (candidate.id === candidateId) {
                return candidate;
            }
        }
        return {};
    }

    function candidateIsSelected(candidateId) {
        return selectedCandidateIds.indexOf(candidateId) >= 0;
    }

    function setCandidateSelected(candidateId, selected) {
        const items = clone(selectedCandidateIds);
        const index = items.indexOf(candidateId);
        if (selected && index < 0) {
            items.push(candidateId);
        } else if (!selected && index >= 0) {
            items.splice(index, 1);
        }
        selectedCandidateIds = items;
    }

    function candidatePreview(value) {
        if (value === undefined || value === null) {
            return "null";
        }
        if (typeof value === "string") {
            return value;
        }
        const preferredKeys = ["title", "name", "comment", "content", "description", "personality", "scenario", "first_mes", "creator_notes", "notes", "value", "prompt"];
        const lines = [];
        if (Array.isArray(value)) {
            for (let i = 0; i < value.length && lines.length < 4; ++i) {
                const text = candidatePreview(value[i]).trim();
                if (text.length > 0 && text !== "null") {
                    lines.push(text);
                }
            }
            return lines.join("\n\n") || "这条建议包含多段结构化内容。";
        }
        if (typeof value === "object") {
            for (let i = 0; i < preferredKeys.length && lines.length < 5; ++i) {
                const key = preferredKeys[i];
                if (value[key] === undefined || value[key] === null) {
                    continue;
                }
                const text = String(value[key]).trim();
                if (text.length > 0) {
                    lines.push(text);
                }
            }
            return lines.join("\n\n") || "这条建议包含结构化内容，可在高级区查看。";
        }
        return String(value);
    }

    function appendCopilotMessage(role, text, detail, error) {
        const items = clone(copilotMessages || []);
        items.push({
            "role": role || "assistant",
            "text": String(text || ""),
            "detail": String(detail || ""),
            "error": Boolean(error)
        });
        copilotMessages = items;
    }

    function clearCopilotConversation() {
        copilotMessages = [];
        candidateReviewText = "";
        candidateReviewResult = {};
        candidateCandidates = [];
        candidateGroups = [];
        candidateAudit = {};
        selectedCandidateIds = [];
    }

    function candidateOperationLabel(candidate) {
        const operation = String(((candidate || {}).target || {}).operation || "set");
        if (operation === "append") {
            return "新增";
        }
        if (operation === "json_patch") {
            return "局部修订";
        }
        return "替换";
    }

    function candidateTargetLabel(candidate) {
        const moduleText = moduleLabel((candidate || {}).module || "");
        const operationText = candidateOperationLabel(candidate);
        return moduleText.length > 0 ? `${operationText}到${moduleText}` : operationText;
    }

    function candidateViewLabel(view) {
        const labels = {
            "persona": "角色卡",
            "worldbook": "世界书",
            "preset": "预设",
            "memory": "记忆",
            "database": "数据库"
        };
        return labels[view] || view;
    }

    function generateCandidates() {
        const prompt = candidatePromptText.trim();
        if (prompt.length === 0) {
            message.warning("请先填写生成需求", 3000);
            return;
        }
        appendCopilotMessage("user", prompt);
        const result = FantarealBridge.generateCardAuthoringCandidates(buildDraft(), prompt, candidateCurrentView, candidateThinkingMode);
        if (!result.ok) {
            message.error(result.message || "轮椅模式生成失败", 6000);
            if ((result.raw_response || "").length > 0) {
                candidateReviewText = result.raw_response;
            }
            appendCopilotMessage("assistant", result.message || "这次没有整理出可填充建议，请补充需求后再试。", result.raw_response || "", true);
            return;
        }
        candidateReviewText = result.raw_response || JSON.stringify(result, null, 2);
        candidateReviewResult = clone(result);
        candidateCandidates = clone(result.candidates || []);
        candidateGroups = clone(result.candidate_groups || []);
        candidateAudit = clone(result.package_audit || {});
        selectedCandidateIds = candidateCandidates.map(candidate => candidate.id).filter(id => Boolean(id));
        appendCopilotMessage("assistant", result.summary || `我整理出 ${selectedCandidateIds.length} 条可填充建议，勾选后再写入草稿。`);
        candidatePromptText = "";
        message.success(result.message || "轮椅模式已整理出建议");
    }

    function normalizeCandidates() {
        let parsed = {};
        try {
            parsed = JSON.parse(candidateReviewText || "{}");
        } catch (error) {
            message.error(`候选 JSON 无法解析：${error.message}`, 5000);
            return;
        }
        const review = Array.isArray(parsed) ? {
            "candidates": parsed
        } : parsed;
        const result = FantarealBridge.normalizeCardAuthoringCandidates(buildDraft(), review);
        if (!result.ok) {
            message.error(result.message || "候选规范化失败", 5000);
            return;
        }
        candidateReviewResult = clone(result);
        candidateCandidates = clone(result.candidates || []);
        candidateGroups = clone(result.candidate_groups || []);
        candidateAudit = clone(result.package_audit || {});
        selectedCandidateIds = candidateCandidates.map(candidate => candidate.id).filter(id => Boolean(id));
        appendCopilotMessage("assistant", result.message || `已从高级 JSON 整理出 ${selectedCandidateIds.length} 条可填充建议。`);
        message.success(result.message || "候选已规范化");
    }

    function applyCandidatesToDraft() {
        if (candidateCandidates.length === 0) {
            normalizeCandidates();
            if (candidateCandidates.length === 0) {
                return;
            }
        }
        if (selectedCandidateIds.length === 0) {
            message.warning("请至少选择一条候选", 3000);
            return;
        }
        const result = FantarealBridge.applyCardAuthoringCandidates(buildDraft(), candidateReviewResult, selectedCandidateIds);
        if (!result.ok) {
            message.error(result.message || "候选应用失败", 5000);
            return;
        }
        applyDraft(result.project);
        candidateReviewResult = clone(result.review || {});
        candidateCandidates = clone(candidateReviewResult.candidates || []);
        candidateGroups = clone(candidateReviewResult.candidate_groups || []);
        candidateAudit = clone(candidateReviewResult.package_audit || {});
        selectedCandidateIds = clone(result.applied_candidate_ids || []);
        markDirty();
        appendCopilotMessage("assistant", result.message || `已把 ${selectedCandidateIds.length} 条建议填充到草稿。`);
        message.success(result.message || "建议已填充到草稿");
    }

    function saveWorkspace() {
        const result = FantarealBridge.saveCardAuthoringWorkspace(buildDraft());
        if (result.ok) {
            message.success(result.message);
            applyDraft(result.project);
        } else {
            message.error(result.message, 5000);
        }
    }

    function saveProject() {
        const filename = titleText.trim().length > 0 ? titleText : (cardNameText.trim().length > 0 ? cardNameText : "untitled");
        const result = FantarealBridge.saveCardAuthoringProject(filename, buildDraft());
        if (result.ok) {
            message.success(result.message);
            applyDraft(result.project);
            refreshProjectItems();
        } else {
            message.error(result.message, 5000);
        }
    }

    function refreshProjects() {
        const result = FantarealBridge.refreshCardAuthoringProjects();
        if (result.ok) {
            refreshProjectItems();
            message.success(result.message);
        } else {
            message.error(result.message, 5000);
        }
    }

    function loadProject(filename) {
        if (dirty) {
            message.warning("请先保存或还原当前修改，再载入项目。", 5000);
            return;
        }
        const result = FantarealBridge.loadCardAuthoringProject(filename);
        if (result.ok) {
            message.success(result.message);
            applyDraft(result.project);
        } else {
            message.error(result.message, 5000);
        }
    }

    function archiveProject(filename) {
        if (dirty) {
            message.warning("请先保存或还原当前修改，再归档项目。", 5000);
            return;
        }
        const result = FantarealBridge.deleteCardAuthoringProject(filename);
        if (result.ok) {
            message.success(result.message);
            refreshProjectItems();
        } else {
            message.error(result.message, 5000);
        }
    }

    function importProject(path) {
        if (dirty) {
            message.warning("请先保存或还原当前修改，再导入项目。", 5000);
            return;
        }
        const result = FantarealBridge.importCardAuthoringProjectFile(path);
        if (result.ok) {
            message.success(result.message);
            applyDraft(result.project);
        } else {
            message.error(result.message, 5000);
        }
    }

    function exportProject(path) {
        const result = FantarealBridge.exportCardAuthoringProjectFile(path, buildDraft());
        if (result.ok) {
            message.success(result.message);
            applyDraft(result.project);
        } else {
            message.error(result.message, 5000);
        }
    }

    function exportProjectToDefaultDir() {
        const result = FantarealBridge.exportCardAuthoringProjectToDefaultDir(buildDraft());
        if (result.ok) {
            message.success(`${result.message}: ${result.exportedPath}`);
            applyDraft(result.project);
        } else {
            message.error(result.message, 5000);
        }
    }

    function validateDraft() {
        const result = FantarealBridge.validateCardAuthoringDraft(buildDraft());
        compiledResult = clone(result);
        compiledWarnings = compiledResult.warnings || [];
        if (result.ok) {
            message.success(result.message);
        } else {
            message.error(result.message, 5000);
        }
    }

    function compileDraft() {
        const result = FantarealBridge.compileCardAuthoringDraft(buildDraft());
        compiledResult = clone(result);
        compiledWarnings = compiledResult.warnings || [];
        if (result.ok) {
            message.success(result.message);
        } else {
            message.error(result.message, 5000);
        }
    }

    function exportCompiledRoleCard(path) {
        const result = FantarealBridge.exportCompiledCardAuthoringRoleCardFile(path, buildDraft());
        compiledResult = clone(result);
        compiledWarnings = compiledResult.warnings || [];
        if (result.ok) {
            message.success(result.message);
        } else {
            message.error(result.message, 5000);
        }
    }

    function exportCompiledRoleCardToDefaultDir() {
        const result = FantarealBridge.exportCompiledCardAuthoringRoleCardToDefaultDir(buildDraft());
        compiledResult = clone(result);
        compiledWarnings = compiledResult.warnings || [];
        if (result.ok) {
            message.success(`${result.message}: ${result.exportedPath}`);
        } else {
            message.error(result.message, 5000);
        }
    }

    function loadCurrentRuntimeDraft() {
        if (dirty) {
            message.warning("请先保存或还原当前修改，再载入当前运行时。", 5000);
            return;
        }
        const result = FantarealBridge.loadCurrentRuntimeCardAuthoringDraft();
        if (result.ok) {
            message.success(result.message);
            applyDraft(result.project);
        } else {
            message.error(result.message, 5000);
        }
    }

    function previewApply() {
        const groups = selectedGroupIds();
        if (groups.length === 0) {
            message.warning("请至少选择一个应用模块", 3000);
            return;
        }
        const draft = buildDraft();
        const result = FantarealBridge.previewCardAuthoringApply(draft, groups);
        previewResult = clone(result);
        previewGroups = previewResult.groups || [];
        previewWarnings = previewResult.warnings || [];
        if (result.ok) {
            previewDraftKey = draftKey(draft);
            previewModuleKey = moduleKey(groups);
            previewStale = false;
            message.success(result.message);
        } else {
            previewDraftKey = "";
            previewModuleKey = "";
            previewStale = true;
            message.error(result.message, 5000);
        }
    }

    function applySelected() {
        const groups = selectedGroupIds();
        if (groups.length === 0) {
            message.warning("请至少选择一个应用模块", 3000);
            return;
        }
        if (!previewMatchesCurrent()) {
            message.warning("请先重新生成预览，确认当前草稿和模块选择后再应用。", 5000);
            return;
        }
        pendingApplyDraft = buildDraft();
        pendingApplyGroups = clone(groups);
        pendingApplyPreview = clone(previewResult);
        applyConfirmModal.open();
    }

    function commitSelectedApply() {
        const result = FantarealBridge.applyCardAuthoringDraft(pendingApplyDraft, pendingApplyGroups);
        if (result.ok) {
            message.success(result.message);
            previewResult = clone(result.preview || pendingApplyPreview || {});
            previewGroups = previewResult.groups || [];
            previewWarnings = previewResult.warnings || [];
            lastOperationResult = applyResultSummary(result);
            previewStale = true;
            previewDraftKey = "";
            previewModuleKey = "";
        } else {
            lastOperationResult = applyResultSummary(result);
            message.error(result.message, 5000);
        }
        pendingApplyDraft = ({});
        pendingApplyGroups = [];
        pendingApplyPreview = ({});
    }

    Component.onCompleted: {
        applyDraft(FantarealBridge.cardAuthoringDraft);
        refreshProjectItems();
    }

    FileDialog {
        id: projectImportDialog
        title: "导入写卡器项目"
        nameFilters: ["写卡器项目 (*.cardwork.json)", "JSON 文件 (*.json)", "所有文件 (*)"]
        onAccepted: root.importProject(selectedFile.toString())
    }

    FileDialog {
        id: projectExportDialog
        title: "导出写卡器项目"
        fileMode: FileDialog.SaveFile
        nameFilters: ["写卡器项目 (*.cardwork.json)", "JSON 文件 (*.json)", "所有文件 (*)"]
        onAccepted: root.exportProject(selectedFile.toString())
    }

    FileDialog {
        id: compiledRoleCardExportDialog
        title: "导出编译角色卡"
        fileMode: FileDialog.SaveFile
        nameFilters: ["角色卡 JSON (*.json)", "所有文件 (*)"]
        onAccepted: root.exportCompiledRoleCard(selectedFile.toString())
    }

    HusModal {
        id: applyConfirmModal

        width: Math.min(Math.max(620, root.width - 160), 820)
        height: Math.min(Math.max(420, root.height - 180), 620)
        modal: true
        closable: false
        maskClosable: false
        position: HusModal.Position_Center
        colorOverlay: HusThemeFunctions.alpha("#000000", HusTheme.isDark ? 0.62 : 0.38)
        footerDelegate: null

        contentDelegate: Item {
            height: applyConfirmModal.height

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 26
                spacing: 16

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    HusText {
                        Layout.fillWidth: true
                        text: "确认应用写卡器变更"
                        font.pixelSize: 24
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                        wrapMode: Text.Wrap
                    }

                    HusTag {
                        text: `${Number((root.pendingApplyPreview.summary || {}).change_count || 0)} 项变更`
                        tagState: HusTag.State_Warning
                    }
                }

                HusText {
                    Layout.fillWidth: true
                    text: "确认后会写入当前运行时文件。写入前会由写卡器创建备份，完成后备份路径会保留在页面里。"
                    color: HusTheme.Primary.colorTextBase
                    wrapMode: Text.Wrap
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: root.pendingApplyGroups

                        delegate: HusTag {
                            text: root.moduleLabel(modelData)
                            tagState: HusTag.State_Processing
                        }
                    }

                    HusTag {
                        text: `提示 ${Number((root.pendingApplyPreview.summary || {}).warning_count || 0)}`
                        tagState: Number((root.pendingApplyPreview.summary || {}).warning_count || 0) > 0 ? HusTag.State_Warning : HusTag.State_Default
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: confirmWarningLayout.implicitHeight + 22
                    radius: 8
                    color: HusThemeFunctions.alpha(Global.accentGold, HusTheme.isDark ? 0.16 : 0.10)
                    border.width: 1
                    border.color: HusThemeFunctions.alpha(Global.accentGold, 0.36)

                    RowLayout {
                        id: confirmWarningLayout
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        HusIconText {
                            iconSource: HusIcon.WarningOutlined
                            iconSize: 17
                            colorIcon: Global.accentGold
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: "这是一次真实写入操作。若刚刚修改过草稿或切换过模块，请取消并重新生成预览。"
                            color: HusTheme.Primary.colorTextPrimary
                            wrapMode: Text.Wrap
                        }
                    }
                }

                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: width
                    contentHeight: confirmPreviewColumn.implicitHeight

                    ColumnLayout {
                        id: confirmPreviewColumn
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: root.pendingApplyPreview.groups || []

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: confirmGroupLayout.implicitHeight + 18
                                radius: 8
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                                RowLayout {
                                    id: confirmGroupLayout
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    HusText {
                                        Layout.fillWidth: true
                                        text: modelData.title || modelData.id || "变更组"
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                        elide: Text.ElideRight
                                    }

                                    HusTag {
                                        text: `${Number(modelData.item_count || 0)} 项`
                                        tagState: Number(modelData.item_count || 0) > 0 ? HusTag.State_Warning : HusTag.State_Default
                                    }
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    HusText {
                        Layout.fillWidth: true
                        text: "应用后如需再次写入，必须重新生成预览。"
                        color: HusTheme.Primary.colorTextSecondary
                        wrapMode: Text.Wrap
                    }

                    HusButton {
                        text: "取消"
                        onClicked: applyConfirmModal.close()
                    }

                    HusButton {
                        text: "确认应用"
                        type: HusButton.Type_Primary
                        onClicked: {
                            applyConfirmModal.close();
                            root.commitSelectedApply();
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: FantarealBridge
        function onScanChanged() {
            root.refreshProjectItems();
            if (!root.dirty) {
                root.applyDraft(FantarealBridge.cardAuthoringDraft);
            }
        }
    }

    HusMessage {
        id: message
        z: 999
        width: root.width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        contentWidth: width
        contentHeight: pageColumn.implicitHeight + 88
        clip: true

        ColumnLayout {
            id: pageColumn
            width: Math.min(parent.width - 88, 1120)
            x: 44
            y: 44
            spacing: 20

            RowLayout {
                width: parent.width
                spacing: 12

                HusText {
                    Layout.fillWidth: true
                    text: "写卡器"
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusTag {
                    visible: root.dirty
                    text: "未保存"
                    tagState: HusTag.State_Warning
                }

                HusTag {
                    text: FantarealBridge.cardAuthoringStatus
                    tagState: HusTag.State_Processing
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: overviewContent.implicitHeight + 56
                accentColor: Global.accentCyan

                ColumnLayout {
                    id: overviewContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 14

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        StatPill {
                            text: "写卡器工程"
                            accentColor: Global.accentCyan
                        }
                        HusTag {
                            text: "data/card_authoring"
                            presetColor: "blue"
                        }
                        HusTag {
                            text: root.databaseEnabled ? "数据库启用" : "数据库关闭"
                            tagState: root.databaseEnabled ? HusTag.State_Success : HusTag.State_Default
                        }
                    }

                    SummaryRows {
                        Layout.fillWidth: true
                        rows: FantarealBridge.cardAuthoringRows
                        labelWidth: 150
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusButton {
                            text: "刷新"
                            onClicked: FantarealBridge.refreshLegacyScan()
                        }

                        HusButton {
                            text: "还原"
                            enabled: root.dirty
                            onClicked: root.applyDraft(FantarealBridge.cardAuthoringDraft)
                        }

                        HusButton {
                            text: "载入当前运行时"
                            type: HusButton.Type_Filled
                            onClicked: root.loadCurrentRuntimeDraft()
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        HusButton {
                            text: "保存工作区"
                            type: HusButton.Type_Primary
                            enabled: root.dirty
                            onClicked: root.saveWorkspace()
                        }

                        HusButton {
                            text: "另存项目"
                            type: HusButton.Type_Filled
                            onClicked: root.saveProject()
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: workshopContent.implicitHeight + 56
                accentColor: Global.accentViolet

                ColumnLayout {
                    id: workshopContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 18

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "演出工坊"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.workshopItems.length} 项`
                            tagState: root.workshopItems.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusSwitch {
                            checked: root.creativeWorkshopEnabled
                            checkedText: "启用"
                            uncheckedText: "关闭"
                            onToggled: {
                                root.creativeWorkshopEnabled = checked;
                                root.creativeWorkshopPresent = true;
                                root.markDirty();
                            }
                        }

                        HusButton {
                            text: "新增事件"
                            type: HusButton.Type_Primary
                            onClicked: root.addWorkshopItem()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedWorkshopIndex >= 0
                            onClicked: root.removeWorkshopItem()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.workshopItems.length > 0

                        Repeater {
                            model: root.workshopItems

                            delegate: HusButton {
                                text: root.workshopTitle(modelData, index)
                                type: index === root.selectedWorkshopIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectWorkshopItem(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.workshopItems.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有演出事件"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedWorkshopIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "事件标识（id）"

                            HusInput {
                                width: parent.width
                                text: root.workshopIdText
                                placeholderText: "workshop_001"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopIdText = text;
                                    root.updateWorkshopField("id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "事件名称"

                            HusInput {
                                width: parent.width
                                text: root.workshopNameText
                                placeholderText: "弹窗 / 音乐 / 图片事件"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopNameText = text;
                                    root.updateWorkshopField("name", text);
                                }
                            }
                        }

                        SettingField {
                            title: "触发模式"

                            HusInput {
                                width: parent.width
                                text: root.workshopTriggerModeText
                                placeholderText: "manual"
                                clearEnabled: "active"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopTriggerModeText = text;
                                    root.updateWorkshopField("triggerMode", text);
                                }
                            }
                        }

                        SettingField {
                            title: "触发阶段规则"

                            HusInput {
                                width: parent.width
                                text: root.workshopTriggerStageText
                                placeholderText: "database.stage.role.stage_1"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopTriggerStageText = text;
                                    root.updateWorkshopField("triggerStage", text);
                                }
                            }
                        }

                        SettingField {
                            title: "温度下限"

                            HusInput {
                                width: parent.width
                                text: root.workshopTriggerTempMinText
                                placeholderText: "0"
                                clearEnabled: "active"
                                iconSource: HusIcon.NumberOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopTriggerTempMinText = text;
                                    root.updateWorkshopField("triggerTempMin", text);
                                }
                            }
                        }

                        SettingField {
                            title: "温度上限"

                            HusInput {
                                width: parent.width
                                text: root.workshopTriggerTempMaxText
                                placeholderText: "1"
                                clearEnabled: "active"
                                iconSource: HusIcon.NumberOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopTriggerTempMaxText = text;
                                    root.updateWorkshopField("triggerTempMax", text);
                                }
                            }
                        }

                        SettingField {
                            title: "动作类型"

                            HusInput {
                                width: parent.width
                                text: root.workshopActionTypeText
                                placeholderText: "note"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopActionTypeText = text;
                                    root.updateWorkshopField("actionType", text);
                                }
                            }
                        }

                        SettingField {
                            title: "弹窗标题"

                            HusInput {
                                width: parent.width
                                text: root.workshopPopupTitleText
                                placeholderText: "弹窗里显示的标题"
                                clearEnabled: "active"
                                iconSource: HusIcon.MessageOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopPopupTitleText = text;
                                    root.updateWorkshopField("popupTitle", text);
                                }
                            }
                        }

                        SettingField {
                            title: "音乐预设"

                            HusInput {
                                width: parent.width
                                text: root.workshopMusicPresetText
                                placeholderText: "rain / piano / custom"
                                clearEnabled: "active"
                                iconSource: HusIcon.MessageOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopMusicPresetText = text;
                                    root.updateWorkshopField("musicPreset", text);
                                }
                            }
                        }

                        SettingField {
                            title: "音乐地址（URL）"

                            HusInput {
                                width: parent.width
                                text: root.workshopMusicUrlText
                                placeholderText: "https://..."
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopMusicUrlText = text;
                                    root.updateWorkshopField("musicUrl", text);
                                }
                            }
                        }

                        SettingField {
                            title: "音量"

                            HusInput {
                                width: parent.width
                                text: root.workshopVolumeText
                                placeholderText: "0.7"
                                clearEnabled: "active"
                                iconSource: HusIcon.MessageOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopVolumeText = text;
                                    root.updateWorkshopField("volume", text);
                                }
                            }
                        }

                        SettingField {
                            title: "图片地址（URL）"

                            HusInput {
                                width: parent.width
                                text: root.workshopImageUrlText
                                placeholderText: "https://..."
                                clearEnabled: "active"
                                iconSource: HusIcon.FileTextOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopImageUrlText = text;
                                    root.updateWorkshopField("imageUrl", text);
                                }
                            }
                        }

                        SettingField {
                            title: "图片说明"

                            HusInput {
                                width: parent.width
                                text: root.workshopImageAltText
                                placeholderText: "图片替代说明"
                                clearEnabled: "active"
                                iconSource: HusIcon.FileTextOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.workshopImageAltText = text;
                                    root.updateWorkshopField("imageAlt", text);
                                }
                            }
                        }

                        SettingField {
                            title: "启用"

                            Flow {
                                width: parent.width
                                spacing: 12

                                HusCheckBox {
                                    text: root.workshopEnabled ? "启用" : "关闭"
                                    checked: root.workshopEnabled
                                    onToggled: {
                                        root.workshopEnabled = checked;
                                        root.updateWorkshopField("enabled", checked);
                                    }
                                }

                                HusCheckBox {
                                    text: "自动播放"
                                    checked: root.workshopAutoplay
                                    onToggled: {
                                        root.workshopAutoplay = checked;
                                        root.updateWorkshopField("autoplay", checked);
                                    }
                                }

                                HusCheckBox {
                                    text: "循环"
                                    checked: root.workshopLoop
                                    onToggled: {
                                        root.workshopLoop = checked;
                                        root.updateWorkshopField("loop", checked);
                                    }
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        visible: root.selectedWorkshopIndex >= 0
                        title: "演出备注"

                        HusTextArea {
                            id: workshopNoteInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 6000
                            autoSize: true
                            resizable: true
                            text: root.workshopNoteText
                            placeholderText: "事件备注或迁移说明"
                            onTextChanged: {
                                if (root.workshopNoteText !== text) {
                                    root.workshopNoteText = text;
                                    root.updateWorkshopField("note", text);
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: projectLibraryContent.implicitHeight + 56
                accentColor: Global.accentBlue

                ColumnLayout {
                    id: projectLibraryContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "项目库"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.projectItems.length} 个项目`
                            tagState: root.projectItems.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusButton {
                            text: "刷新"
                            onClicked: root.refreshProjects()
                        }

                        HusButton {
                            text: "导入"
                            type: HusButton.Type_Primary
                            onClicked: projectImportDialog.open()
                        }

                        HusButton {
                            text: "导出"
                            type: HusButton.Type_Filled
                            onClicked: projectExportDialog.open()
                        }

                        HusButton {
                            text: "默认导出"
                            type: HusButton.Type_Outlined
                            onClicked: root.exportProjectToDefaultDir()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        HusTag {
                            text: "data/card_authoring/projects"
                            presetColor: "blue"
                        }

                        HusTag {
                            text: ".cardwork.json"
                            tagState: HusTag.State_Default
                        }
                    }

                    Repeater {
                        model: root.projectItems

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 72
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(modelData.ok === false ? Global.accentGold : HusTheme.Primary.colorBorder, 0.30)

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    HusText {
                                        Layout.fillWidth: true
                                        text: modelData.title || modelData.filename || "未命名项目"
                                        elide: Text.ElideRight
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        text: modelData.ok === false ? (modelData.message || "项目文件无法读取") : root.projectMetaText(modelData)
                                        elide: Text.ElideRight
                                        font.pixelSize: 12
                                        color: modelData.ok === false ? Global.accentGold : HusTheme.Primary.colorTextSecondary
                                    }
                                }

                                HusTag {
                                    text: modelData.filename || ".cardwork.json"
                                    presetColor: "blue"
                                }

                                HusButton {
                                    text: "载入"
                                    enabled: modelData.ok !== false
                                    onClicked: root.loadProject(modelData.filename)
                                }

                                HusButton {
                                    text: "归档"
                                    type: HusButton.Type_Outlined
                                    onClicked: root.archiveProject(modelData.filename)
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 60
                        radius: 8
                        visible: root.projectItems.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有保存的写卡器项目"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: editorContent.implicitHeight + 56
                accentColor: Global.accentViolet

                ColumnLayout {
                    id: editorContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 22

                    HusText {
                        Layout.fillWidth: true
                        text: "项目与主卡"
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "项目标题"

                            HusInput {
                                width: parent.width
                                text: root.titleText
                                placeholderText: "例如：艾琳完整卡"
                                clearEnabled: "active"
                                iconSource: HusIcon.EditOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.titleText = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "主卡名称"

                            HusInput {
                                width: parent.width
                                text: root.cardNameText
                                placeholderText: "主卡角色名称"
                                clearEnabled: "active"
                                iconSource: HusIcon.UserOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.cardNameText = text;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "标签"

                        HusInput {
                            width: parent.width
                            text: root.tagsText
                            placeholderText: "幻想, 长篇, 角色关系"
                            clearEnabled: "active"
                            iconSource: HusIcon.TagsOutlined
                            iconPosition: HusInput.Position_Left
                            onTextEdited: {
                                root.tagsText = text;
                                root.markDirty();
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "描述（description）"

                            HusTextArea {
                                id: descriptionInput
                                width: parent.width
                                minRows: 4
                                maxRows: 8
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.descriptionText
                                placeholderText: "主卡角色定义、外观与背景"
                                onTextChanged: {
                                    if (root.descriptionText !== text) {
                                        root.descriptionText = text;
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "性格（personality）"

                            HusTextArea {
                                id: personalityInput
                                width: parent.width
                                minRows: 4
                                maxRows: 8
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.personalityText
                                placeholderText: "性格、语气、行为偏好"
                                onTextChanged: {
                                    if (root.personalityText !== text) {
                                        root.personalityText = text;
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "场景（scenario）"

                            HusTextArea {
                                id: scenarioInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.scenarioText
                                placeholderText: "世界观、当前场景和互动前提"
                                onTextChanged: {
                                    if (root.scenarioText !== text) {
                                        root.scenarioText = text;
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "开场消息（first_mes）"

                            HusTextArea {
                                id: firstMessageInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.firstMessageText
                                placeholderText: "主卡第一条开场消息"
                                onTextChanged: {
                                    if (root.firstMessageText !== text) {
                                        root.firstMessageText = text;
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "示例对话（mes_example）"

                            HusTextArea {
                                id: mesExampleInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.mesExampleText
                                placeholderText: "示例对话与动作节奏"
                                onTextChanged: {
                                    if (root.mesExampleText !== text) {
                                        root.mesExampleText = text;
                                        root.markDirty();
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "作者备注（creator_notes）"

                            HusTextArea {
                                id: creatorNotesInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.creatorNotesText
                                placeholderText: "隐藏纪律、写作边界和维护说明"
                                onTextChanged: {
                                    if (root.creatorNotesText !== text) {
                                        root.creatorNotesText = text;
                                        root.markDirty();
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "多角色（personas）"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.personaItems.length} 项`
                            tagState: root.personaItems.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusButton {
                            text: "新增多角色"
                            type: HusButton.Type_Primary
                            onClicked: root.addPersonaItem()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedPersonaIndex >= 0
                            onClicked: root.removePersonaItem()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.personaItems.length > 0

                        Repeater {
                            model: root.personaItems

                            delegate: HusButton {
                                text: root.personaTitle(modelData, index)
                                type: index === root.selectedPersonaIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectPersonaItem(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.personaItems.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有多角色"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedPersonaIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "多角色编号（id）"

                            HusInput {
                                width: parent.width
                                text: root.personaIdText
                                placeholderText: "2"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.personaIdText = text;
                                    root.updatePersonaField("id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "多角色名称"

                            HusInput {
                                width: parent.width
                                text: root.personaNameText
                                placeholderText: "多角色名称"
                                clearEnabled: "active"
                                iconSource: HusIcon.UserOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.personaNameText = text;
                                    root.updatePersonaField("name", text);
                                }
                            }
                        }

                        SettingField {
                            Layout.columnSpan: pageColumn.width < 880 ? 1 : 2
                            title: "多角色标签"

                            HusInput {
                                width: parent.width
                                text: root.personaTagsText
                                placeholderText: "配角, 群像, 阶段"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.personaTagsText = text;
                                    root.updatePersonaField("tags", root.splitTagsText(text));
                                }
                            }
                        }

                        SettingField {
                            title: "多角色描述（description）"

                            HusTextArea {
                                id: personaDescriptionInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.personaDescriptionText
                                placeholderText: "该多角色的身份、背景和关系定位"
                                onTextChanged: {
                                    if (root.personaDescriptionText !== text) {
                                        root.personaDescriptionText = text;
                                        root.updatePersonaField("description", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "多角色性格（personality）"

                            HusTextArea {
                                id: personaPersonalityInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.personaPersonalityText
                                placeholderText: "该多角色的性格、口吻与行为方式"
                                onTextChanged: {
                                    if (root.personaPersonalityText !== text) {
                                        root.personaPersonalityText = text;
                                        root.updatePersonaField("personality", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "多角色场景（scenario）"

                            HusTextArea {
                                id: personaScenarioInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.personaScenarioText
                                placeholderText: "该多角色的默认场景或分支前提"
                                onTextChanged: {
                                    if (root.personaScenarioText !== text) {
                                        root.personaScenarioText = text;
                                        root.updatePersonaField("scenario", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "多角色备注（creator_notes）"

                            HusTextArea {
                                id: personaCreatorNotesInput
                                width: parent.width
                                minRows: 3
                                maxRows: 7
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.personaCreatorNotesText
                                placeholderText: "该多角色的隐藏规则、边界或维护备注"
                                onTextChanged: {
                                    if (root.personaCreatorNotesText !== text) {
                                        root.personaCreatorNotesText = text;
                                        root.updatePersonaField("creator_notes", text);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: databaseContent.implicitHeight + 56
                accentColor: Global.accentGreen

                ColumnLayout {
                    id: databaseContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 22

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        HusText {
                            Layout.fillWidth: true
                            text: "数据库"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusSwitch {
                            checked: root.databaseEnabled
                            checkedText: "启用"
                            uncheckedText: "关闭"
                            onToggled: {
                                root.databaseEnabled = checked;
                                root.markDirty();
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "数据库备注（notes）"

                        HusTextArea {
                            id: databaseNotesInput
                            width: parent.width
                            minRows: 3
                            maxRows: 6
                            maxLength: 6000
                            autoSize: true
                            resizable: true
                            text: root.databaseNotesText
                            placeholderText: "记录数据库设计说明、变量含义或迁移备注"
                            onTextChanged: {
                                if (root.databaseNotesText !== text) {
                                    root.databaseNotesText = text;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "变量"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.databaseVariables.length} 项`
                            tagState: root.databaseVariables.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusButton {
                            text: "新增变量"
                            type: HusButton.Type_Primary
                            onClicked: root.addVariable()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedVariableIndex >= 0
                            onClicked: root.removeVariable()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.databaseVariables.length > 0

                        Repeater {
                            model: root.databaseVariables

                            delegate: HusButton {
                                text: root.variableTitle(modelData, index)
                                type: index === root.selectedVariableIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectVariable(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.databaseVariables.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有变量"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedVariableIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "变量键（key）"

                            HusInput {
                                width: parent.width
                                text: root.variableKeyText
                                placeholderText: "affection"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.variableKeyText = text;
                                    root.updateVariableField("key", text);
                                }
                            }
                        }

                        SettingField {
                            title: "变量名称"

                            HusInput {
                                width: parent.width
                                text: root.variableLabelText
                                placeholderText: "好感度"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.variableLabelText = text;
                                    root.updateVariableField("label", text);
                                }
                            }
                        }

                        SettingField {
                            title: "类型"

                            HusInput {
                                width: parent.width
                                text: root.variableTypeText
                                placeholderText: "text / number / bool"
                                clearEnabled: "active"
                                iconSource: HusIcon.DatabaseOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.variableTypeText = text;
                                    root.updateVariableField("value_type", text);
                                }
                            }
                        }

                        SettingField {
                            title: "作用域（scope）"

                            HusInput {
                                width: parent.width
                                text: root.variableScopeText
                                placeholderText: "role"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.variableScopeText = text;
                                    root.updateVariableField("scope", text);
                                }
                            }
                        }

                        SettingField {
                            title: "初始值"

                            HusInput {
                                width: parent.width
                                text: root.variableInitialValueText
                                placeholderText: "0"
                                clearEnabled: "active"
                                iconSource: HusIcon.DatabaseOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.variableInitialValueText = text;
                                    root.updateVariableField("initial_value", text);
                                }
                            }
                        }

                        SettingField {
                            title: "写入策略"

                            HusInput {
                                width: parent.width
                                text: root.variableWritePolicyText
                                placeholderText: "manual / worker / locked"
                                clearEnabled: "active"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.variableWritePolicyText = text;
                                    root.updateVariableField("write_policy", text);
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedVariableIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "变量说明"

                            HusTextArea {
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.variableDescriptionText
                                placeholderText: "这项变量如何被写入和解释"
                                onTextChanged: {
                                    if (root.variableDescriptionText !== text) {
                                        root.variableDescriptionText = text;
                                        root.updateVariableField("description", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "变量备注（notes）"

                            HusTextArea {
                                id: variableNotesInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.variableNotesText
                                placeholderText: "内部备注、迁移来源或候选生成提示"
                                onTextChanged: {
                                    if (root.variableNotesText !== text) {
                                        root.variableNotesText = text;
                                        root.updateVariableField("notes", text);
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "阶段规则"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.databaseStages.length} 项`
                            tagState: root.databaseStages.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusButton {
                            text: "新增阶段规则"
                            type: HusButton.Type_Primary
                            onClicked: root.addStage()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedStageIndex >= 0
                            onClicked: root.removeStage()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.databaseStages.length > 0

                        Repeater {
                            model: root.databaseStages

                            delegate: HusButton {
                                text: root.stageTitle(modelData, index)
                                type: index === root.selectedStageIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectStage(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.databaseStages.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有阶段规则"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedStageIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "角色"

                            HusInput {
                                width: parent.width
                                text: root.stageRoleText
                                placeholderText: "role"
                                clearEnabled: "active"
                                iconSource: HusIcon.IdcardOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.stageRoleText = text;
                                    root.updateStageField("role_id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "阶段键（key）"

                            HusInput {
                                width: parent.width
                                text: root.stageKeyText
                                placeholderText: "trust"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.stageKeyText = text;
                                    root.updateStageField("stage_key", text);
                                }
                            }
                        }

                        SettingField {
                            title: "标题"

                            HusInput {
                                width: parent.width
                                text: root.stageTitleText
                                placeholderText: "信任阶段"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.stageTitleText = text;
                                    root.updateStageField("title", text);
                                }
                            }
                        }

                        SettingField {
                            title: "触发条件"

                            HusInput {
                                width: parent.width
                                text: root.stageConditionText
                                placeholderText: "affection >= 10"
                                clearEnabled: "active"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.stageConditionText = text;
                                    root.updateStageField("condition", text);
                                }
                            }
                        }

                        SettingField {
                            title: "激活标签（active_tag）"

                            HusInput {
                                width: parent.width
                                text: root.stageActiveTagText
                                placeholderText: "database.stage.role.trust"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.stageActiveTagText = text;
                                    root.updateStageField("active_tag", text);
                                }
                            }
                        }

                        SettingField {
                            title: "发出标签（emits_tags）"

                            HusInput {
                                width: parent.width
                                text: root.stageEmitsTagsText
                                placeholderText: "database.stage.role.trust"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.stageEmitsTagsText = text;
                                    root.updateStageField("emits_tags", root.splitTagsText(text));
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedStageIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "阶段说明"

                            HusTextArea {
                                id: stageDescriptionInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.stageDescriptionText
                                placeholderText: "这个阶段规则代表什么阶段"
                                onTextChanged: {
                                    if (root.stageDescriptionText !== text) {
                                        root.stageDescriptionText = text;
                                        root.updateStageField("description", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "阶段备注（notes）"

                            HusTextArea {
                                id: stageNotesInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.stageNotesText
                                placeholderText: "内部备注、迁移来源或候选生成提示"
                                onTextChanged: {
                                    if (root.stageNotesText !== text) {
                                        root.stageNotesText = text;
                                        root.updateStageField("notes", text);
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "状态快照字段"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.databaseSnapshotFields.length} 项`
                            tagState: root.databaseSnapshotFields.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusButton {
                            text: "新增快照字段"
                            type: HusButton.Type_Primary
                            onClicked: root.addSnapshotField()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedSnapshotFieldIndex >= 0
                            onClicked: root.removeSnapshotField()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.databaseSnapshotFields.length > 0

                        Repeater {
                            model: root.databaseSnapshotFields

                            delegate: HusButton {
                                text: root.snapshotFieldTitle(modelData, index)
                                type: index === root.selectedSnapshotFieldIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectSnapshotField(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.databaseSnapshotFields.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有状态快照字段"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedSnapshotFieldIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "角色"

                            HusInput {
                                width: parent.width
                                text: root.snapshotRoleText
                                placeholderText: "role"
                                clearEnabled: "active"
                                iconSource: HusIcon.IdcardOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.snapshotRoleText = text;
                                    root.updateSnapshotField("role_id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "字段键（key）"

                            HusInput {
                                width: parent.width
                                text: root.snapshotKeyText
                                placeholderText: "mood"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.snapshotKeyText = text;
                                    root.updateSnapshotField("key", text);
                                }
                            }
                        }

                        SettingField {
                            title: "字段名称"

                            HusInput {
                                width: parent.width
                                text: root.snapshotLabelText
                                placeholderText: "当前情绪"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.snapshotLabelText = text;
                                    root.updateSnapshotField("label", text);
                                }
                            }
                        }

                        SettingField {
                            title: "启用与显示"

                            RowLayout {
                                width: parent.width
                                spacing: 12

                                HusSwitch {
                                    checked: root.snapshotEnabled
                                    checkedText: "启用"
                                    uncheckedText: "关闭"
                                    onToggled: {
                                        root.snapshotEnabled = checked;
                                        root.updateSnapshotField("enabled", checked);
                                    }
                                }

                                HusSwitch {
                                    checked: root.snapshotDisplay
                                    checkedText: "显示"
                                    uncheckedText: "隐藏"
                                    onToggled: {
                                        root.snapshotDisplay = checked;
                                        root.updateSnapshotField("display", checked);
                                    }
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedSnapshotFieldIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "生成说明"
                            description: "告诉 DatabaseWorker 如何从本轮回复里提取这个字段。"

                            HusTextArea {
                                id: snapshotInstructionInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.snapshotInstructionText
                                placeholderText: "根据本轮上下文生成该状态快照字段。"
                                onTextChanged: {
                                    if (root.snapshotInstructionText !== text) {
                                        root.snapshotInstructionText = text;
                                        root.updateSnapshotField("instruction", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "字段备注（notes）"

                            HusTextArea {
                                id: snapshotNotesInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.snapshotNotesText
                                placeholderText: "内部备注、迁移来源或候选生成提示"
                                onTextChanged: {
                                    if (root.snapshotNotesText !== text) {
                                        root.snapshotNotesText = text;
                                        root.updateSnapshotField("notes", text);
                                    }
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "数据库标签"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.databaseTags.length} 项`
                            tagState: root.databaseTags.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusButton {
                            text: "新增标签"
                            type: HusButton.Type_Primary
                            onClicked: root.addDatabaseTag()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedTagIndex >= 0
                            onClicked: root.removeDatabaseTag()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.databaseTags.length > 0

                        Repeater {
                            model: root.databaseTags

                            delegate: HusButton {
                                text: root.databaseTagTitle(modelData, index)
                                type: index === root.selectedTagIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectDatabaseTag(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.databaseTags.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有数据库标签"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedTagIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "标签（tag）"

                            HusInput {
                                width: parent.width
                                text: root.databaseTagText
                                placeholderText: "database.stage.role.trust"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.databaseTagText = text;
                                    root.updateDatabaseTagField("tag", text);
                                }
                            }
                        }

                        SettingField {
                            title: "标题"

                            HusInput {
                                width: parent.width
                                text: root.databaseTagTitleText
                                placeholderText: "信任阶段词条"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.databaseTagTitleText = text;
                                    root.updateDatabaseTagField("title", text);
                                }
                            }
                        }

                        SettingField {
                            title: "主关键词（trigger）"

                            HusInput {
                                width: parent.width
                                text: root.databaseTagTriggerText
                                placeholderText: "trust"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.databaseTagTriggerText = text;
                                    root.updateDatabaseTagField("trigger", text);
                                }
                            }
                        }

                        SettingField {
                            title: "目标模块（target）"

                            HusInput {
                                width: parent.width
                                text: root.databaseTagTargetText
                                placeholderText: "worldbook"
                                clearEnabled: "active"
                                iconSource: HusIcon.DatabaseOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.databaseTagTargetText = text;
                                    root.updateDatabaseTagField("target", text);
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedTagIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "标签说明"

                            HusTextArea {
                                id: databaseTagDescriptionInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.databaseTagDescriptionText
                                placeholderText: "这个标签会被哪些模块消费"
                                onTextChanged: {
                                    if (root.databaseTagDescriptionText !== text) {
                                        root.databaseTagDescriptionText = text;
                                        root.updateDatabaseTagField("description", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "标签备注（notes）"

                            HusTextArea {
                                id: databaseTagNotesInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 4000
                                autoSize: true
                                resizable: true
                                text: root.databaseTagNotesText
                                placeholderText: "内部备注、迁移来源或候选生成提示"
                                onTextChanged: {
                                    if (root.databaseTagNotesText !== text) {
                                        root.databaseTagNotesText = text;
                                        root.updateDatabaseTagField("notes", text);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: runtimeContent.implicitHeight + 56
                accentColor: Global.accentBlue

                ColumnLayout {
                    id: runtimeContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 22

                    HusText {
                        Layout.fillWidth: true
                        text: "世界书、预设与记忆"
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        HusTag {
                            text: `世界书 ${root.worldbookEntries.length} 项`
                            tagState: root.worldbookEntries.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusTag {
                            text: `提示 ${root.presetExtraPrompts.length + root.presetPromptGroups.length} 项`
                            tagState: (root.presetExtraPrompts.length + root.presetPromptGroups.length) > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusTag {
                            text: `记忆 ${root.memoryItems.length} 项`
                            tagState: root.memoryItems.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "世界书"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusButton {
                            text: root.worldbookSettingsVisible ? "收起默认策略" : "默认策略"
                            type: HusButton.Type_Filled
                            onClicked: root.worldbookSettingsVisible = !root.worldbookSettingsVisible
                        }

                        HusButton {
                            text: "新增词条"
                            type: HusButton.Type_Primary
                            onClicked: root.addWorldbookEntry()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedWorldbookIndex >= 0
                            onClicked: root.removeWorldbookEntry()
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.worldbookSettingsVisible
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "世界书启用"

                            HusCheckBox {
                                text: root.worldbookSettings.enabled === undefined || Boolean(root.worldbookSettings.enabled) ? "启用" : "关闭"
                                checked: root.worldbookSettings.enabled === undefined ? true : Boolean(root.worldbookSettings.enabled)
                                onToggled: root.updateWorldbookSetting("enabled", checked)
                            }
                        }

                        SettingField {
                            title: "调试"

                            HusCheckBox {
                                text: Boolean(root.worldbookSettings.debug_enabled) ? "启用" : "关闭"
                                checked: Boolean(root.worldbookSettings.debug_enabled)
                                onToggled: root.updateWorldbookSetting("debug_enabled", checked)
                            }
                        }

                        SettingField {
                            title: "最大命中数（max_hits）"

                            HusInput {
                                width: parent.width
                                text: String(root.worldbookSettings.max_hits === undefined ? 3 : root.worldbookSettings.max_hits)
                                placeholderText: "3"
                                iconSource: HusIcon.NumberOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: root.updateWorldbookSetting("max_hits", text)
                            }
                        }

                        SettingField {
                            title: "默认词条类型"

                            HusInput {
                                width: parent.width
                                text: root.worldbookSettings.default_entry_type || "keyword"
                                placeholderText: "keyword / constant / external_tag"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: root.updateWorldbookSetting("default_entry_type", text)
                            }
                        }

                        SettingField {
                            title: "默认注入位置"

                            HusInput {
                                width: parent.width
                                text: root.worldbookSettings.default_insertion_position || "after_char_defs"
                                placeholderText: "after_char_defs"
                                iconSource: HusIcon.PushpinOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: root.updateWorldbookSetting("default_insertion_position", text)
                            }
                        }

                        SettingField {
                            title: "默认提示词层"

                            HusInput {
                                width: parent.width
                                text: root.worldbookSettings.default_prompt_layer || "follow_position"
                                placeholderText: "follow_position"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: root.updateWorldbookSetting("default_prompt_layer", text)
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root.worldbookEntries.length > 0
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            HusText {
                                text: "词条筛选"
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: root.worldbookFilterSummaryText()
                                font.pixelSize: 12
                                color: HusTheme.Primary.colorTextSecondary
                                elide: Text.ElideRight
                            }

                            HusButton {
                                text: "清空筛选"
                                type: HusButton.Type_Outlined
                                enabled: root.worldbookGroupFilter !== "__all__" || root.worldbookSearchText.length > 0
                                onClicked: {
                                    root.worldbookGroupFilter = "__all__";
                                    root.worldbookSearchText = "";
                                    root.worldbookEntryPickerExpanded = false;
                                }
                            }
                        }

                        HusInput {
                            Layout.fillWidth: true
                            text: root.worldbookSearchText
                            placeholderText: "按标题、组别、触发词、内容、备注搜索"
                            clearEnabled: "active"
                            iconSource: HusIcon.TagsOutlined
                            iconPosition: HusInput.Position_Left
                            onTextEdited: {
                                root.worldbookSearchText = text;
                                root.worldbookEntryPickerExpanded = false;
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 8

                            Repeater {
                                model: root.worldbookGroupOptions()

                                delegate: HusButton {
                                    text: `${modelData.label} ${modelData.count}`
                                    type: modelData.key === root.worldbookGroupFilter ? HusButton.Type_Primary : HusButton.Type_Outlined
                                    onClicked: {
                                        root.worldbookGroupFilter = modelData.key;
                                        root.worldbookEntryPickerExpanded = false;
                                    }
                                }
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            visible: root.filteredWorldbookEntries().length > 0

                            Repeater {
                                model: root.visibleWorldbookPickerEntries()

                                delegate: HusButton {
                                    text: root.worldbookEntryPickerLabel(modelData)
                                    type: modelData.sourceIndex === root.selectedWorldbookIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                    onClicked: root.selectWorldbookEntry(modelData.sourceIndex)
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 52
                            radius: 8
                            visible: root.filteredWorldbookEntries().length === 0
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                            HusText {
                                anchors.centerIn: parent
                                text: "没有匹配的世界书词条"
                                font.pixelSize: 13
                                color: HusTheme.Primary.colorTextSecondary
                            }
                        }

                        HusButton {
                            text: root.worldbookEntryPickerExpanded ? "收起词条列表" : `显示全部 ${root.filteredWorldbookEntries().length} 条`
                            type: HusButton.Type_Outlined
                            visible: root.filteredWorldbookEntries().length > root.visibleWorldbookPickerEntries().length || root.worldbookEntryPickerExpanded
                            onClicked: root.worldbookEntryPickerExpanded = !root.worldbookEntryPickerExpanded
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.worldbookEntries.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有世界书词条"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedWorldbookIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "标识（id）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookIdText
                                placeholderText: "wb_entry_001"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookIdText = text;
                                    root.updateWorldbookField("id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "标题"

                            HusInput {
                                width: parent.width
                                text: root.worldbookTitleText
                                placeholderText: "地点、人物或规则"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookTitleText = text;
                                    root.updateWorldbookField("title", text);
                                }
                            }
                        }

                        SettingField {
                            title: "触发词（trigger）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookTriggerText
                                placeholderText: "多个别名可用逗号分隔"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookTriggerText = text;
                                    root.updateWorldbookField("trigger", text);
                                }
                            }
                        }

                        SettingField {
                            title: "副关键词（secondary_trigger）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookSecondaryTriggerText
                                placeholderText: "可留空；例如：婚后, 成亲"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookSecondaryTriggerText = text;
                                    root.updateWorldbookField("secondary_trigger", text);
                                }
                            }
                        }

                        SettingField {
                            title: "词条类型（entry_type）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookEntryTypeText
                                placeholderText: "keyword / constant / external_tag"
                                clearEnabled: "active"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookEntryTypeText = text;
                                    root.updateWorldbookField("entry_type", text);
                                }
                            }
                        }

                        SettingField {
                            title: "分组（group）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookGroupText
                                placeholderText: "database / lore"
                                clearEnabled: "active"
                                iconSource: HusIcon.DatabaseOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookGroupText = text;
                                    root.updateWorldbookField("group", text);
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.selectedWorldbookIndex >= 0 && pageColumn.width >= 880
                        spacing: 18

                        SettingField {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignTop
                            title: "词条内容"

                            HusTextArea {
                                id: worldbookContentInput
                                width: parent.width
                                minRows: 3
                                maxRows: 8
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.worldbookContentText
                                placeholderText: "会注入到世界书上下文的内容"
                                onTextChanged: {
                                    if (root.worldbookContentText !== text) {
                                        root.worldbookContentText = text;
                                        root.updateWorldbookField("content", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            Layout.preferredWidth: Math.max(220, Math.min(280, pageColumn.width * 0.22))
                            Layout.maximumWidth: 300
                            Layout.alignment: Qt.AlignTop
                            title: "备注（comment）"

                            HusTextArea {
                                id: worldbookCommentInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 2400
                                autoSize: true
                                resizable: true
                                text: root.worldbookCommentText
                                placeholderText: "内部备注或迁移来源"
                                onTextChanged: {
                                    if (root.worldbookCommentText !== text) {
                                        root.worldbookCommentText = text;
                                        root.updateWorldbookField("comment", text);
                                    }
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root.selectedWorldbookIndex >= 0 && pageColumn.width < 880
                        spacing: 18

                        SettingField {
                            Layout.fillWidth: true
                            title: "词条内容"

                            HusTextArea {
                                width: parent.width
                                minRows: 3
                                maxRows: 8
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.worldbookContentText
                                placeholderText: "会注入到世界书上下文的内容"
                                onTextChanged: {
                                    if (root.worldbookContentText !== text) {
                                        root.worldbookContentText = text;
                                        root.updateWorldbookField("content", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            Layout.fillWidth: true
                            title: "备注（comment）"

                            HusTextArea {
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 2400
                                autoSize: true
                                resizable: true
                                text: root.worldbookCommentText
                                placeholderText: "内部备注或迁移来源"
                                onTextChanged: {
                                    if (root.worldbookCommentText !== text) {
                                        root.worldbookCommentText = text;
                                        root.updateWorldbookField("comment", text);
                                    }
                                }
                            }
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.selectedWorldbookIndex >= 0

                        HusButton {
                            text: root.worldbookTriggerAdvancedVisible ? "收起触发规则" : "触发规则"
                            type: root.worldbookTriggerAdvancedVisible ? HusButton.Type_Primary : HusButton.Type_Outlined
                            onClicked: root.worldbookTriggerAdvancedVisible = !root.worldbookTriggerAdvancedVisible
                        }

                        HusButton {
                            text: root.worldbookInjectionAdvancedVisible ? "收起注入位置" : "注入位置"
                            type: root.worldbookInjectionAdvancedVisible ? HusButton.Type_Primary : HusButton.Type_Outlined
                            onClicked: root.worldbookInjectionAdvancedVisible = !root.worldbookInjectionAdvancedVisible
                        }

                        HusButton {
                            text: root.worldbookStateAdvancedVisible ? "收起数据库联动" : "数据库联动"
                            type: root.worldbookStateAdvancedVisible ? HusButton.Type_Primary : HusButton.Type_Outlined
                            onClicked: root.worldbookStateAdvancedVisible = !root.worldbookStateAdvancedVisible
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedWorldbookIndex >= 0 && root.worldbookTriggerAdvancedVisible
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "主触发匹配（match_mode）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookMatchModeText
                                placeholderText: "any / all"
                                onTextEdited: {
                                    root.worldbookMatchModeText = text;
                                    root.updateWorldbookField("match_mode", text);
                                }
                            }
                        }

                        SettingField {
                            title: "副触发匹配（secondary_mode）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookSecondaryModeText
                                placeholderText: "all / any"
                                onTextEdited: {
                                    root.worldbookSecondaryModeText = text;
                                    root.updateWorldbookField("secondary_mode", text);
                                }
                            }
                        }

                        SettingField {
                            title: "分组运算（group_operator）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookGroupOperatorText
                                placeholderText: "and / or"
                                onTextEdited: {
                                    root.worldbookGroupOperatorText = text;
                                    root.updateWorldbookField("group_operator", text);
                                }
                            }
                        }

                        SettingField {
                            title: "触发概率（chance）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookChanceText
                                placeholderText: "100"
                                iconSource: HusIcon.PercentageOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookChanceText = text;
                                    root.updateWorldbookField("chance", text);
                                }
                            }
                        }

                        SettingField {
                            title: "粘滞轮数（sticky_turns）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookStickyTurnsText
                                placeholderText: "0"
                                onTextEdited: {
                                    root.worldbookStickyTurnsText = text;
                                    root.updateWorldbookField("sticky_turns", text);
                                }
                            }
                        }

                        SettingField {
                            title: "冷却轮数（cooldown_turns）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookCooldownTurnsText
                                placeholderText: "0"
                                onTextEdited: {
                                    root.worldbookCooldownTurnsText = text;
                                    root.updateWorldbookField("cooldown_turns", text);
                                }
                            }
                        }

                        SettingField {
                            title: "大小写"

                            HusCheckBox {
                                text: root.worldbookCaseSensitive ? "区分" : "不区分"
                                checked: root.worldbookCaseSensitive
                                onToggled: {
                                    root.worldbookCaseSensitive = checked;
                                    root.updateWorldbookField("case_sensitive", checked);
                                }
                            }
                        }

                        SettingField {
                            title: "整词匹配"

                            HusCheckBox {
                                text: root.worldbookWholeWord ? "启用" : "关闭"
                                checked: root.worldbookWholeWord
                                onToggled: {
                                    root.worldbookWholeWord = checked;
                                    root.updateWorldbookField("whole_word", checked);
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedWorldbookIndex >= 0 && root.worldbookInjectionAdvancedVisible
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "排序（order）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookOrderText
                                placeholderText: "100"
                                iconSource: HusIcon.NumberOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookOrderText = text;
                                    root.updateWorldbookField("order", text);
                                    root.updateWorldbookField("priority", text);
                                }
                            }
                        }

                        SettingField {
                            title: "插入位置（insertion_position）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookInsertionPositionText
                                placeholderText: "after_char_defs"
                                onTextEdited: {
                                    root.worldbookInsertionPositionText = text;
                                    root.updateWorldbookField("insertion_position", text);
                                }
                            }
                        }

                        SettingField {
                            title: "注入深度（injection_depth）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookInjectionDepthText
                                placeholderText: "0"
                                onTextEdited: {
                                    root.worldbookInjectionDepthText = text;
                                    root.updateWorldbookField("injection_depth", text);
                                }
                            }
                        }

                        SettingField {
                            title: "注入角色（injection_role）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookInjectionRoleText
                                placeholderText: "system / user / assistant"
                                onTextEdited: {
                                    root.worldbookInjectionRoleText = text;
                                    root.updateWorldbookField("injection_role", text);
                                }
                            }
                        }

                        SettingField {
                            title: "注入顺序（injection_order）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookInjectionOrderText
                                placeholderText: "100"
                                onTextEdited: {
                                    root.worldbookInjectionOrderText = text;
                                    root.updateWorldbookField("injection_order", text);
                                }
                            }
                        }

                        SettingField {
                            title: "提示词层（prompt_layer）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookPromptLayerText
                                placeholderText: "follow_position / stable / current_state"
                                onTextEdited: {
                                    root.worldbookPromptLayerText = text;
                                    root.updateWorldbookField("prompt_layer", text);
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedWorldbookIndex >= 0 && root.worldbookStateAdvancedVisible
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "启用词条"

                            HusCheckBox {
                                text: root.worldbookEnabled ? "启用" : "关闭"
                                checked: root.worldbookEnabled
                                onToggled: {
                                    root.worldbookEnabled = checked;
                                    root.updateWorldbookField("enabled", checked);
                                }
                            }
                        }

                        SettingField {
                            title: "允许递归"

                            HusCheckBox {
                                text: root.worldbookRecursiveEnabled ? "允许" : "关闭"
                                checked: root.worldbookRecursiveEnabled
                                onToggled: {
                                    root.worldbookRecursiveEnabled = checked;
                                    root.updateWorldbookField("recursive_enabled", checked);
                                }
                            }
                        }

                        SettingField {
                            title: "阻止后续递归"

                            HusCheckBox {
                                text: root.worldbookPreventFurtherRecursion ? "阻止" : "不阻止"
                                checked: root.worldbookPreventFurtherRecursion
                                onToggled: {
                                    root.worldbookPreventFurtherRecursion = checked;
                                    root.updateWorldbookField("prevent_further_recursion", checked);
                                }
                            }
                        }

                        SettingField {
                            title: "外部来源（external_source）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookExternalSourceText
                                placeholderText: "database / state_snapshot"
                                onTextEdited: {
                                    root.worldbookExternalSourceText = text;
                                    root.updateWorldbookField("external_source", text);
                                }
                            }
                        }

                        SettingField {
                            title: "激活标签（activation_tags）"

                            HusInput {
                                width: parent.width
                                text: root.worldbookActivationTagsText
                                placeholderText: "用逗号分隔"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.worldbookActivationTagsText = text;
                                    root.updateWorldbookField("activation_tags", text);
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "预设"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: root.presetActivePresetId || "active preset"
                            tagState: HusTag.State_Processing
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "当前预设 ID（active_preset_id）"

                            HusInput {
                                width: parent.width
                                text: root.presetActivePresetId
                                placeholderText: "preset_default"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetActivePresetId = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "预设名称"

                            HusInput {
                                width: parent.width
                                text: root.presetNameText
                                placeholderText: "写卡器预设"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetNameText = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "预设启用"

                            HusCheckBox {
                                text: root.presetEnabled ? "启用" : "关闭"
                                checked: root.presetEnabled
                                onToggled: {
                                    root.presetEnabled = checked;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "基础系统提示词（base_system_prompt）"

                        HusTextArea {
                            id: presetBaseSystemPromptInput
                            width: parent.width
                            minRows: 3
                            maxRows: 8
                            maxLength: 16000
                            autoSize: true
                            resizable: true
                            text: root.presetBaseSystemPromptText
                            placeholderText: "描述模型如何读取主卡、世界书、记忆和数据库状态"
                            onTextChanged: {
                                if (root.presetBaseSystemPromptText !== text) {
                                    root.presetBaseSystemPromptText = text;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    HusText {
                        Layout.fillWidth: true
                        text: "模块开关"
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 12

                        Repeater {
                            model: root.presetModuleDefs

                            delegate: HusCheckBox {
                                text: modelData.label
                                checked: Boolean(root.presetModules[modelData.key])
                                onToggled: root.updatePresetModule(modelData.key, checked)
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: root.presetTopLabel()
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusButton {
                            text: root.selectedPresetCollection === "extra_prompts" ? "切到预设组" : "切到额外提示"
                            type: HusButton.Type_Filled
                            onClicked: root.selectPresetCollection(root.selectedPresetCollection === "extra_prompts" ? "prompt_groups" : "extra_prompts")
                        }

                        HusButton {
                            text: root.selectedPresetCollection === "prompt_groups" ? "新增预设组" : "新增额外提示"
                            type: HusButton.Type_Primary
                            onClicked: root.addPresetItem()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedPresetItemIndex >= 0
                            onClicked: root.removePresetItem()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.currentPresetItems().length > 0

                        Repeater {
                            model: root.currentPresetItems()

                            delegate: HusButton {
                                text: root.currentPresetItemTitle(modelData, index)
                                type: index === root.selectedPresetItemIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectPresetItem(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.currentPresetItems().length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: root.selectedPresetCollection === "prompt_groups" ? "还没有预设组" : "还没有额外提示"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "extra_prompts" && root.selectedPresetItemIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "标识（id）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemIdText
                                placeholderText: "extra_prompt_001"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetItemIdText = text;
                                    root.updatePresetItemField("id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "名称"

                            HusInput {
                                width: parent.width
                                text: root.presetItemNameText
                                placeholderText: "提示名称"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetItemNameText = text;
                                    root.updatePresetItemField("name", text);
                                }
                            }
                        }

                        SettingField {
                            title: "顺序（order）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemOrderText
                                placeholderText: "100"
                                iconSource: HusIcon.NumberOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetItemOrderText = text;
                                    root.updatePresetItemField("order", text);
                                }
                            }
                        }

                        SettingField {
                            title: "启用"

                            HusCheckBox {
                                text: root.presetItemEnabled ? "启用" : "关闭"
                                checked: root.presetItemEnabled
                                onToggled: {
                                    root.presetItemEnabled = checked;
                                    root.updatePresetItemField("enabled", checked);
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "extra_prompts" && root.selectedPresetItemIndex >= 0
                        title: "提示内容"

                        HusTextArea {
                            id: presetItemContentInput
                            width: parent.width
                            minRows: 3
                            maxRows: 8
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.presetItemContentText
                            placeholderText: "会合并进当前预设的额外提示"
                            onTextChanged: {
                                if (root.presetItemContentText !== text) {
                                    root.presetItemContentText = text;
                                    root.updatePresetItemField("content", text);
                                }
                            }
                        }
                    }

                    HusButton {
                        visible: root.selectedPresetCollection === "extra_prompts" && root.selectedPresetItemIndex >= 0
                        text: root.presetItemAdvancedVisible ? "收起额外提示高级字段" : "额外提示高级字段"
                        type: root.presetItemAdvancedVisible ? HusButton.Type_Primary : HusButton.Type_Outlined
                        onClicked: root.presetItemAdvancedVisible = !root.presetItemAdvancedVisible
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "extra_prompts" && root.selectedPresetItemIndex >= 0 && root.presetItemAdvancedVisible
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "插入位置（placement）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemPlacementText
                                placeholderText: "after_character / at_depth"
                                onTextEdited: {
                                    root.presetItemPlacementText = text;
                                    root.updatePresetItemField("placement", text);
                                }
                            }
                        }

                        SettingField {
                            title: "类型（kind）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemKindText
                                placeholderText: "style / output_rule / memory"
                                onTextEdited: {
                                    root.presetItemKindText = text;
                                    root.updatePresetItemField("kind", text);
                                }
                            }
                        }

                        SettingField {
                            title: "强度（strength）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemStrengthText
                                placeholderText: "soft / hard"
                                onTextEdited: {
                                    root.presetItemStrengthText = text;
                                    root.updatePresetItemField("strength", text);
                                }
                            }
                        }

                        SettingField {
                            title: "角色（role）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemRoleText
                                placeholderText: "system / user / assistant"
                                onTextEdited: {
                                    root.presetItemRoleText = text;
                                    root.updatePresetItemField("role", text);
                                }
                            }
                        }

                        SettingField {
                            title: "深度（depth）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemDepthText
                                placeholderText: "0"
                                onTextEdited: {
                                    root.presetItemDepthText = text;
                                    root.updatePresetItemField("depth", text);
                                }
                            }
                        }

                        SettingField {
                            title: "预算（tokenBudget）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemTokenBudgetText
                                placeholderText: "可留空"
                                onTextEdited: {
                                    root.presetItemTokenBudgetText = text;
                                    root.updatePresetItemField("tokenBudget", text);
                                }
                            }
                        }

                        SettingField {
                            title: "必选（required）"

                            HusCheckBox {
                                text: root.presetItemRequired ? "必选" : "可选"
                                checked: root.presetItemRequired
                                onToggled: {
                                    root.presetItemRequired = checked;
                                    root.updatePresetItemField("required", checked);
                                }
                            }
                        }

                        SettingField {
                            title: "激活标签（activation_tags）"

                            HusInput {
                                width: parent.width
                                text: root.presetItemActivationTagsText
                                placeholderText: "用逗号分隔"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetItemActivationTagsText = text;
                                    root.updatePresetItemField("activation_tags", text);
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetItemIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "预设组 ID"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupIdText
                                placeholderText: "prompt_group_001"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetGroupIdText = text;
                                    root.updatePresetItemField("id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "预设组名称"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupNameText
                                placeholderText: "规则组名称"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetGroupNameText = text;
                                    root.updatePresetItemField("name", text);
                                }
                            }
                        }

                        SettingField {
                            title: "选择模式（selection_mode）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupSelectionModeText
                                placeholderText: "single / multiple"
                                onTextEdited: {
                                    root.presetGroupSelectionModeText = text;
                                    root.updatePresetItemField("selection_mode", text);
                                }
                            }
                        }

                        SettingField {
                            title: "顺序（order）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupOrderText
                                placeholderText: "100"
                                iconSource: HusIcon.NumberOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetGroupOrderText = text;
                                    root.updatePresetItemField("order", text);
                                }
                            }
                        }

                        SettingField {
                            title: "启用"

                            HusCheckBox {
                                text: root.presetGroupEnabled ? "启用" : "关闭"
                                checked: root.presetGroupEnabled
                                onToggled: {
                                    root.presetGroupEnabled = checked;
                                    root.updatePresetItemField("enabled", checked);
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetItemIndex >= 0
                        title: "已选组内项（selected_ids）"

                        HusInput {
                            width: parent.width
                            text: root.presetGroupSelectedIdsText
                            placeholderText: "用逗号分隔；也可以在组内项上勾选"
                            iconSource: HusIcon.TagsOutlined
                            iconPosition: HusInput.Position_Left
                            onTextEdited: {
                                root.presetGroupSelectedIdsText = text;
                                root.updatePresetItemField("selected_ids", text);
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetItemIndex >= 0
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "组内提示"
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusButton {
                            text: "新增组内项"
                            type: HusButton.Type_Primary
                            onClicked: root.addPresetGroupItem()
                        }

                        HusButton {
                            text: "移除组内项"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedPresetGroupItemIndex >= 0
                            onClicked: root.removePresetGroupItem()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.selectedPresetCollection === "prompt_groups" && root.currentPresetGroupItems().length > 0

                        Repeater {
                            model: root.currentPresetGroupItems()

                            delegate: HusCheckBox {
                                text: root.presetGroupItemTitle(modelData, index)
                                checked: (((root.currentPresetItems()[root.selectedPresetItemIndex] || {}).selected_ids || []).indexOf(modelData.id || "") >= 0)
                                onToggled: {
                                    root.selectPresetGroupItem(index);
                                    root.togglePresetGroupSelectedId(modelData.id || "", checked);
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetItemIndex >= 0 && root.currentPresetGroupItems().length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "这个预设组还没有组内提示"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetGroupItemIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "组内项 ID"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemIdText
                                placeholderText: "prompt_group_item_001"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetGroupItemIdText = text;
                                    root.updatePresetGroupItemField("id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "组内项名称"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemNameText
                                placeholderText: "选项名称"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetGroupItemNameText = text;
                                    root.updatePresetGroupItemField("name", text);
                                }
                            }
                        }

                        SettingField {
                            title: "启用"

                            HusCheckBox {
                                text: root.presetGroupItemEnabled ? "启用" : "关闭"
                                checked: root.presetGroupItemEnabled
                                onToggled: {
                                    root.presetGroupItemEnabled = checked;
                                    root.updatePresetGroupItemField("enabled", checked);
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetGroupItemIndex >= 0
                        title: "组内项内容"

                        HusTextArea {
                            id: presetGroupItemContentInput
                            width: parent.width
                            minRows: 3
                            maxRows: 8
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.presetGroupItemContentText
                            placeholderText: "这个选项被选中后注入的提示内容"
                            onTextChanged: {
                                if (root.presetGroupItemContentText !== text) {
                                    root.presetGroupItemContentText = text;
                                    root.updatePresetGroupItemField("content", text);
                                }
                            }
                        }
                    }

                    HusButton {
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetGroupItemIndex >= 0
                        text: root.presetGroupItemAdvancedVisible ? "收起组内项高级字段" : "组内项高级字段"
                        type: root.presetGroupItemAdvancedVisible ? HusButton.Type_Primary : HusButton.Type_Outlined
                        onClicked: root.presetGroupItemAdvancedVisible = !root.presetGroupItemAdvancedVisible
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedPresetCollection === "prompt_groups" && root.selectedPresetGroupItemIndex >= 0 && root.presetGroupItemAdvancedVisible
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "插入位置（placement）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemPlacementText
                                placeholderText: "after_character / at_depth"
                                onTextEdited: {
                                    root.presetGroupItemPlacementText = text;
                                    root.updatePresetGroupItemField("placement", text);
                                }
                            }
                        }

                        SettingField {
                            title: "类型（kind）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemKindText
                                placeholderText: "style / output_rule / memory"
                                onTextEdited: {
                                    root.presetGroupItemKindText = text;
                                    root.updatePresetGroupItemField("kind", text);
                                }
                            }
                        }

                        SettingField {
                            title: "强度（strength）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemStrengthText
                                placeholderText: "soft / hard"
                                onTextEdited: {
                                    root.presetGroupItemStrengthText = text;
                                    root.updatePresetGroupItemField("strength", text);
                                }
                            }
                        }

                        SettingField {
                            title: "角色（role）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemRoleText
                                placeholderText: "system / user / assistant"
                                onTextEdited: {
                                    root.presetGroupItemRoleText = text;
                                    root.updatePresetGroupItemField("role", text);
                                }
                            }
                        }

                        SettingField {
                            title: "深度（depth）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemDepthText
                                placeholderText: "0"
                                onTextEdited: {
                                    root.presetGroupItemDepthText = text;
                                    root.updatePresetGroupItemField("depth", text);
                                }
                            }
                        }

                        SettingField {
                            title: "预算（tokenBudget）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemTokenBudgetText
                                placeholderText: "可留空"
                                onTextEdited: {
                                    root.presetGroupItemTokenBudgetText = text;
                                    root.updatePresetGroupItemField("tokenBudget", text);
                                }
                            }
                        }

                        SettingField {
                            title: "必选（required）"

                            HusCheckBox {
                                text: root.presetGroupItemRequired ? "必选" : "可选"
                                checked: root.presetGroupItemRequired
                                onToggled: {
                                    root.presetGroupItemRequired = checked;
                                    root.updatePresetGroupItemField("required", checked);
                                }
                            }
                        }

                        SettingField {
                            title: "激活标签（activation_tags）"

                            HusInput {
                                width: parent.width
                                text: root.presetGroupItemActivationTagsText
                                placeholderText: "用逗号分隔"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetGroupItemActivationTagsText = text;
                                    root.updatePresetGroupItemField("activation_tags", text);
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "记忆草稿"
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusButton {
                            text: "新增记忆"
                            type: HusButton.Type_Primary
                            onClicked: root.addMemoryItem()
                        }

                        HusButton {
                            text: "移除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedMemoryIndex >= 0
                            onClicked: root.removeMemoryItem()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: root.memoryItems.length > 0

                        Repeater {
                            model: root.memoryItems

                            delegate: HusButton {
                                text: root.memoryTitle(modelData, index)
                                type: index === root.selectedMemoryIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.selectMemoryItem(index)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        radius: 8
                        visible: root.memoryItems.length === 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有记忆草稿"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedMemoryIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "标识（id）"

                            HusInput {
                                width: parent.width
                                text: root.memoryIdText
                                placeholderText: "memory_001"
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.memoryIdText = text;
                                    root.updateMemoryField("id", text);
                                }
                            }
                        }

                        SettingField {
                            title: "标题"

                            HusInput {
                                width: parent.width
                                text: root.memoryTitleText
                                placeholderText: "重要记忆"
                                clearEnabled: "active"
                                iconSource: HusIcon.ProjectOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.memoryTitleText = text;
                                    root.updateMemoryField("title", text);
                                }
                            }
                        }

                        SettingField {
                            title: "标签（tags）"

                            HusInput {
                                width: parent.width
                                text: root.memoryTagsText
                                placeholderText: "关系, 设定"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.memoryTagsText = text;
                                    root.updateMemoryField("tags", root.splitTagsText(text));
                                }
                            }
                        }

                        SettingField {
                            title: "状态"

                            HusInput {
                                width: parent.width
                                text: root.memoryStatusText
                                placeholderText: "active / archived"
                                clearEnabled: "active"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.memoryStatusText = text;
                                    root.updateMemoryField("memory_status", text);
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.selectedMemoryIndex >= 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "记忆内容"

                            HusTextArea {
                                id: memoryContentInput
                                width: parent.width
                                minRows: 3
                                maxRows: 8
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.memoryContentText
                                placeholderText: "会追加到当前角色 memories.json"
                                onTextChanged: {
                                    if (root.memoryContentText !== text) {
                                        root.memoryContentText = text;
                                        root.updateMemoryField("content", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "备注（notes）"

                            HusTextArea {
                                id: memoryNotesInput
                                width: parent.width
                                minRows: 3
                                maxRows: 8
                                maxLength: 2400
                                autoSize: true
                                resizable: true
                                text: root.memoryNotesText
                                placeholderText: "内部备注或迁移来源"
                                onTextChanged: {
                                    if (root.memoryNotesText !== text) {
                                        root.memoryNotesText = text;
                                        root.updateMemoryField("notes", text);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: candidateContent.implicitHeight + 56
                accentColor: Global.accentGreen

                ColumnLayout {
                    id: candidateContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 18

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        HusText {
                            Layout.fillWidth: true
                            text: "轮椅模式"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusButton {
                            text: "发送给轮椅"
                            type: HusButton.Type_Primary
                            enabled: root.candidatePromptText.trim().length > 0
                            onClicked: root.generateCandidates()
                        }

                        HusButton {
                            text: root.candidateAdvancedVisible ? "收起高级" : "高级"
                            type: HusButton.Type_Filled
                            onClicked: root.candidateAdvancedVisible = !root.candidateAdvancedVisible
                        }

                        HusButton {
                            text: "填充选中建议"
                            type: HusButton.Type_Primary
                            enabled: root.candidateCandidates.length > 0
                            onClicked: root.applyCandidatesToDraft()
                        }

                        HusButton {
                            text: "清空对话"
                            type: HusButton.Type_Filled
                            enabled: root.copilotMessages.length > 0 || root.candidateCandidates.length > 0
                            onClicked: root.clearCopilotConversation()
                        }
                    }

                    SettingField {
                        title: "对话"

                        HusTextArea {
                            id: candidatePromptInput
                            width: parent.width
                            minRows: 2
                            maxRows: 6
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.candidatePromptText
                            placeholderText: "直接说你想生成、补写或修改什么。"
                            onTextChanged: {
                                if (root.candidatePromptText !== text) {
                                    root.candidatePromptText = text;
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: copilotMessagesLayout.implicitHeight + 20
                        radius: 8
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.18 : 0.48)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                        ColumnLayout {
                            id: copilotMessagesLayout
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10

                            Rectangle {
                                Layout.fillWidth: true
                                visible: root.copilotMessages.length === 0
                                implicitHeight: emptyCopilotText.implicitHeight + 18
                                radius: 8
                                color: HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.14 : 0.08)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.24)

                                HusText {
                                    id: emptyCopilotText
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: "轮椅模式会读取当前草稿，整理成确认后才填充的建议。"
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.Wrap
                                }
                            }

                            Repeater {
                                model: root.copilotMessages

                                delegate: Rectangle {
                                    property var messageData: modelData
                                    property bool fromUser: String(messageData.role || "") === "user"

                                    Layout.fillWidth: true
                                    implicitHeight: copilotMessageLayout.implicitHeight + 18
                                    radius: 8
                                    color: fromUser
                                        ? HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.24 : 0.12)
                                        : (messageData.error
                                            ? HusThemeFunctions.alpha(Global.accentGold, HusTheme.isDark ? 0.18 : 0.12)
                                            : HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.22 : 0.56))
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(fromUser ? Global.accentBlue : (messageData.error ? Global.accentGold : HusTheme.Primary.colorBorder), 0.28)

                                    ColumnLayout {
                                        id: copilotMessageLayout
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 6

                                        HusText {
                                            Layout.fillWidth: true
                                            text: fromUser ? "你" : "轮椅模式"
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: messageData.text || ""
                                            color: HusTheme.Primary.colorTextPrimary
                                            wrapMode: Text.Wrap
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            visible: root.candidateAdvancedVisible && String(messageData.detail || "").length > 0
                                            text: messageData.detail || ""
                                            color: HusTheme.Primary.colorTextSecondary
                                            wrapMode: Text.WrapAnywhere
                                            maximumLineCount: 6
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: ["persona", "worldbook", "preset", "memory", "database"]

                            delegate: HusButton {
                                text: root.candidateViewLabel(modelData)
                                type: root.candidateCurrentView === modelData ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.candidateCurrentView = modelData
                            }
                        }

                        HusButton {
                        text: "快速"
                            type: root.candidateThinkingMode === "fast" ? HusButton.Type_Primary : HusButton.Type_Outlined
                            onClicked: root.candidateThinkingMode = "fast"
                        }

                        HusButton {
                        text: "深度"
                            type: root.candidateThinkingMode === "deep" ? HusButton.Type_Primary : HusButton.Type_Outlined
                            onClicked: root.candidateThinkingMode = "deep"
                        }
                    }

                    SettingField {
                        visible: root.candidateAdvancedVisible
                        title: "候选 JSON（高级）"

                        HusTextArea {
                            id: candidateJsonInput
                            width: parent.width
                            minRows: 4
                            maxRows: 10
                            maxLength: 80000
                            autoSize: true
                            resizable: true
                            text: root.candidateReviewText
                            placeholderText: "{\"candidates\": [...]}"
                            onTextChanged: {
                                if (root.candidateReviewText !== text) {
                                    root.candidateReviewText = text;
                                }
                            }
                        }
                    }

                    HusButton {
                        visible: root.candidateAdvancedVisible
                        text: "规范化高级 JSON"
                        type: HusButton.Type_Filled
                        onClicked: root.normalizeCandidates()
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        HusTag {
                            text: `建议 ${root.candidateCandidates.length}`
                            tagState: root.candidateCandidates.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        HusTag {
                            text: `已选 ${root.selectedCandidateIds.length}`
                            tagState: root.selectedCandidateIds.length > 0 ? HusTag.State_Warning : HusTag.State_Default
                        }

                        HusTag {
                            text: `拒绝 ${Number(root.candidateReviewResult.rejected_count || 0)}`
                            tagState: Number(root.candidateReviewResult.rejected_count || 0) > 0 ? HusTag.State_Warning : HusTag.State_Default
                        }

                        HusTag {
                            text: (root.candidateAudit.ready === false) ? "待补齐" : "闭环就绪"
                            tagState: (root.candidateAudit.ready === false) ? HusTag.State_Warning : HusTag.State_Success
                            visible: root.candidateCandidates.length > 0
                        }
                    }

                    Repeater {
                        model: root.candidateAudit.warnings || []

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: auditWarningLayout.implicitHeight + 18
                            radius: 8
                            color: HusThemeFunctions.alpha(Global.accentGold, HusTheme.isDark ? 0.16 : 0.12)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(Global.accentGold, 0.38)

                            RowLayout {
                                id: auditWarningLayout
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                HusIconText {
                                    iconSource: HusIcon.WarningOutlined
                                    iconSize: 16
                                    colorIcon: Global.accentGold
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: modelData
                                    color: HusTheme.Primary.colorTextPrimary
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }

                    Repeater {
                        model: root.candidateGroups

                        delegate: Rectangle {
                            id: candidateGroup

                            property var groupData: modelData

                            Layout.fillWidth: true
                            implicitHeight: candidateGroupLayout.implicitHeight + 20
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.28)

                            ColumnLayout {
                                id: candidateGroupLayout
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    HusText {
                                        Layout.fillWidth: true
                                        text: candidateGroup.groupData.group_title || candidateGroup.groupData.group_id || "可填充建议"
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                        elide: Text.ElideRight
                                    }

                                    HusTag {
                                        text: `${(candidateGroup.groupData.candidate_ids || []).length} 条`
                                        tagState: HusTag.State_Default
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: candidateGroup.groupData.reason || ""
                                    visible: text.length > 0
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.Wrap
                                }

                                Repeater {
                                    model: candidateGroup.groupData.candidate_ids || []

                                    delegate: Rectangle {
                                        id: candidateRow

                                        property var candidateData: root.candidateById(modelData)

                                        Layout.fillWidth: true
                                        implicitHeight: candidateRowLayout.implicitHeight + 18
                                        radius: 8
                                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.18 : 0.52)
                                        border.width: 1
                                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.22)

                                        ColumnLayout {
                                            id: candidateRowLayout
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 8

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 8

                                                HusCheckBox {
                                                    checked: root.candidateIsSelected(candidateRow.candidateData.id)
                                                    onToggled: root.setCandidateSelected(candidateRow.candidateData.id, checked)
                                                }

                                                HusText {
                                                    Layout.fillWidth: true
                                                    text: candidateRow.candidateData.label || candidateRow.candidateData.id || "候选"
                                                    font.pixelSize: 14
                                                    font.weight: Font.DemiBold
                                                    color: HusTheme.Primary.colorTextPrimary
                                                    elide: Text.ElideRight
                                                }

                                                HusTag {
                                                    text: root.moduleLabel(candidateRow.candidateData.module || "")
                                                    tagState: HusTag.State_Default
                                                }

                                                HusTag {
                                                    text: root.candidateOperationLabel(candidateRow.candidateData)
                                                    tagState: ((candidateRow.candidateData.target || {}).operation === "append") ? HusTag.State_Success : HusTag.State_Warning
                                                }
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                text: root.candidateTargetLabel(candidateRow.candidateData)
                                                color: HusTheme.Primary.colorTextSecondary
                                                wrapMode: Text.Wrap
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                text: candidateRow.candidateData.reason || ""
                                                visible: text.length > 0
                                                color: HusTheme.Primary.colorTextSecondary
                                                wrapMode: Text.Wrap
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                text: root.candidatePreview(candidateRow.candidateData.after)
                                                color: HusTheme.Primary.colorTextPrimary
                                                wrapMode: Text.WrapAnywhere
                                                maximumLineCount: 5
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: applyContent.implicitHeight + 56
                accentColor: Global.accentGold

                ColumnLayout {
                    id: applyContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 18

                    HusText {
                        Layout.fillWidth: true
                        text: "预览与应用"
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        HusButton {
                            text: "校验草稿"
                            type: HusButton.Type_Filled
                            onClicked: root.validateDraft()
                        }

                        HusButton {
                            text: "编译角色卡"
                            type: HusButton.Type_Filled
                            onClicked: root.compileDraft()
                        }

                        HusButton {
                            text: "导出角色卡"
                            type: HusButton.Type_Primary
                            onClicked: compiledRoleCardExportDialog.open()
                        }

                        HusButton {
                            text: "默认导出"
                            type: HusButton.Type_Filled
                            onClicked: root.exportCompiledRoleCardToDefaultDir()
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: Boolean((root.compiledResult || {}).message)
                        implicitHeight: compiledResultLayout.implicitHeight + 18
                        radius: 8
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.28)

                        ColumnLayout {
                            id: compiledResultLayout
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                HusText {
                                    Layout.fillWidth: true
                                    text: (root.compiledResult || {}).message || ""
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                    elide: Text.ElideRight
                                }

                                HusTag {
                                    text: `提示 ${Number((root.compiledResult || {}).warning_count || root.compiledWarnings.length || 0)}`
                                    tagState: root.compiledWarnings.length > 0 ? HusTag.State_Warning : HusTag.State_Success
                                }
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: 8
                                visible: Boolean((root.compiledResult || {}).summary)

                                HusTag {
                                    text: `变量 ${Number(((root.compiledResult || {}).summary || {}).variable_count || 0)}`
                                    tagState: HusTag.State_Default
                                }

                                HusTag {
                                    text: `阶段规则 ${Number(((root.compiledResult || {}).summary || {}).stage_count || 0)}`
                                    tagState: HusTag.State_Default
                                }

                                HusTag {
                                    text: `快照字段 ${Number(((root.compiledResult || {}).summary || {}).snapshot_field_count || 0)}`
                                    tagState: HusTag.State_Default
                                }

                                HusTag {
                                    text: `数据库标签 ${Number(((root.compiledResult || {}).summary || {}).database_tag_count || 0)}`
                                    tagState: HusTag.State_Default
                                }
                            }

                            HusText {
                                Layout.fillWidth: true
                                visible: Boolean((root.compiledResult || {}).exportedPath)
                                text: (root.compiledResult || {}).exportedPath || ""
                                color: HusTheme.Primary.colorTextSecondary
                                wrapMode: Text.WrapAnywhere
                            }

                            Repeater {
                                model: root.compiledWarnings

                                delegate: HusText {
                                    Layout.fillWidth: true
                                    text: modelData
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 18

                        HusCheckBox {
                            text: "主卡"
                            checked: root.applyPersona
                            onToggled: {
                                root.applyPersona = checked;
                                root.markPreviewStale();
                            }
                        }

                        HusCheckBox {
                            text: "数据库"
                            checked: root.applyDatabase
                            onToggled: {
                                root.applyDatabase = checked;
                                root.markPreviewStale();
                            }
                        }
                        HusCheckBox {
                            text: "世界书"
                            checked: root.applyWorldbook
                            onToggled: {
                                root.applyWorldbook = checked;
                                root.markPreviewStale();
                            }
                        }
                        HusCheckBox {
                            text: "预设"
                            checked: root.applyPreset
                            onToggled: {
                                root.applyPreset = checked;
                                root.markPreviewStale();
                            }
                        }
                        HusCheckBox {
                            text: "记忆"
                            checked: root.applyMemory
                            onToggled: {
                                root.applyMemory = checked;
                                root.markPreviewStale();
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Item {
                            Layout.fillWidth: true
                        }

                        HusButton {
                            text: "生成预览"
                            type: HusButton.Type_Filled
                            onClicked: root.previewApply()
                        }

                        HusButton {
                            text: "应用选中模块"
                            type: HusButton.Type_Primary
                            enabled: root.previewMatchesCurrent()
                            onClicked: root.applySelected()
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        HusTag {
                            text: `变更组 ${Number((root.previewResult.summary || {}).group_count || 0)}`
                            tagState: HusTag.State_Default
                        }

                        HusTag {
                            text: `变更项 ${Number((root.previewResult.summary || {}).change_count || 0)}`
                            tagState: Number((root.previewResult.summary || {}).change_count || 0) > 0 ? HusTag.State_Warning : HusTag.State_Default
                        }

                        HusTag {
                            text: `提示 ${Number((root.previewResult.summary || {}).warning_count || root.previewWarnings.length || 0)}`
                            tagState: root.previewWarnings.length > 0 ? HusTag.State_Warning : HusTag.State_Default
                        }

                        HusTag {
                            text: root.previewMatchesCurrent() ? "预览可应用" : (root.previewStale && root.previewGroups.length > 0 ? "预览已过期" : "需生成预览")
                            tagState: root.previewMatchesCurrent() ? HusTag.State_Success : HusTag.State_Warning
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: root.previewStale && root.previewGroups.length > 0
                        implicitHeight: stalePreviewLayout.implicitHeight + 18
                        radius: 8
                        color: HusThemeFunctions.alpha(Global.accentGold, HusTheme.isDark ? 0.15 : 0.10)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(Global.accentGold, 0.34)

                        RowLayout {
                            id: stalePreviewLayout
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 10

                            HusIconText {
                                iconSource: HusIcon.WarningOutlined
                                iconSize: 16
                                colorIcon: Global.accentGold
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: "当前显示的是旧预览或上次应用结果。请重新生成预览后再应用。"
                                color: HusTheme.Primary.colorTextPrimary
                                wrapMode: Text.Wrap
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: Boolean((root.lastOperationResult || {}).message)
                        implicitHeight: lastOperationLayout.implicitHeight + 20
                        radius: 8
                        color: HusThemeFunctions.alpha(Global.accentGreen, HusTheme.isDark ? 0.14 : 0.08)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(Global.accentGreen, 0.30)

                        ColumnLayout {
                            id: lastOperationLayout
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                HusText {
                                    Layout.fillWidth: true
                                    text: (root.lastOperationResult || {}).message || "应用完成"
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                    elide: Text.ElideRight
                                }

                                HusTag {
                                    text: `${Number((root.lastOperationResult || {}).appliedCount || 0)} 模块`
                                    tagState: HusTag.State_Success
                                }

                                HusTag {
                                    text: `${Number((root.lastOperationResult || {}).backupCount || 0)} 备份`
                                    tagState: Number((root.lastOperationResult || {}).backupCount || 0) > 0 ? HusTag.State_Processing : HusTag.State_Default
                                }
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: `模块：${(root.lastOperationResult || {}).moduleText || "无"} · 时间：${(root.lastOperationResult || {}).timeText || ""}`
                                color: HusTheme.Primary.colorTextSecondary
                                wrapMode: Text.Wrap
                            }

                            Repeater {
                                model: (root.lastOperationResult || {}).backups || []

                                delegate: HusText {
                                    Layout.fillWidth: true
                                    text: modelData
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }
                    }

                    Repeater {
                        model: root.previewWarnings

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: warningLayout.implicitHeight + 18
                            radius: 8
                            color: HusThemeFunctions.alpha(Global.accentGold, HusTheme.isDark ? 0.16 : 0.12)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(Global.accentGold, 0.38)

                            RowLayout {
                                id: warningLayout
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                HusIconText {
                                    iconSource: modelData.severity === "info" ? HusIcon.InfoCircleOutlined : HusIcon.WarningOutlined
                                    iconSize: 16
                                    colorIcon: Global.accentGold
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: modelData.message || modelData.id || ""
                                    color: HusTheme.Primary.colorTextPrimary
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }

                    Repeater {
                        model: root.previewGroups

                        delegate: Rectangle {
                            id: previewGroupCard

                            property var groupData: modelData

                            Layout.fillWidth: true
                            implicitHeight: previewGroupLayout.implicitHeight + 20
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.28)

                            ColumnLayout {
                                id: previewGroupLayout
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    HusText {
                                        Layout.fillWidth: true
                                        text: previewGroupCard.groupData.title || previewGroupCard.groupData.id || "变更组"
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                        elide: Text.ElideRight
                                    }

                                    HusTag {
                                        text: `${Number(previewGroupCard.groupData.item_count || 0)} 项`
                                        tagState: Number(previewGroupCard.groupData.item_count || 0) > 0 ? HusTag.State_Warning : HusTag.State_Default
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: previewGroupCard.groupData.description || ""
                                    visible: text.length > 0
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.Wrap
                                }

                                Repeater {
                                    model: previewGroupCard.groupData.changes || []

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: changeLayout.implicitHeight + 18
                                        radius: 8
                                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.18 : 0.52)
                                        border.width: 1
                                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.22)

                                        ColumnLayout {
                                            id: changeLayout
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            spacing: 8

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 8

                                                HusTag {
                                                    text: modelData.action === "create" ? "新增" : (modelData.action === "remove" ? "移除" : "更新")
                                                    tagState: modelData.action === "create" ? HusTag.State_Success : HusTag.State_Warning
                                                }

                                                HusText {
                                                    Layout.fillWidth: true
                                                    text: modelData.label || modelData.field || "字段"
                                                    font.pixelSize: 14
                                                    font.weight: Font.DemiBold
                                                    color: HusTheme.Primary.colorTextPrimary
                                                    elide: Text.ElideRight
                                                }

                                                HusTag {
                                                    text: modelData.path || modelData.field || ""
                                                    tagState: HusTag.State_Default
                                                }
                                            }

                                            GridLayout {
                                                Layout.fillWidth: true
                                                columns: pageColumn.width < 860 ? 1 : 2
                                                columnSpacing: 10
                                                rowSpacing: 8

                                                Rectangle {
                                                    Layout.fillWidth: true
                                                    implicitHeight: beforeText.implicitHeight + 20
                                                    radius: 8
                                                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                                                    border.width: 1
                                                    border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.18)

                                                    ColumnLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: 10
                                                        spacing: 4

                                                        HusText {
                                                            text: "当前"
                                                            font.pixelSize: 12
                                                            color: HusTheme.Primary.colorTextSecondary
                                                        }

                                                        HusText {
                                                            id: beforeText
                                                            Layout.fillWidth: true
                                                            text: modelData.before_preview || "未设置"
                                                            color: HusTheme.Primary.colorTextPrimary
                                                            wrapMode: Text.WrapAnywhere
                                                        }
                                                    }
                                                }

                                                Rectangle {
                                                    Layout.fillWidth: true
                                                    implicitHeight: afterText.implicitHeight + 20
                                                    radius: 8
                                                    color: HusThemeFunctions.alpha(Global.accentGreen, HusTheme.isDark ? 0.12 : 0.08)
                                                    border.width: 1
                                                    border.color: HusThemeFunctions.alpha(Global.accentGreen, 0.24)

                                                    ColumnLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: 10
                                                        spacing: 4

                                                        HusText {
                                                            text: "应用后"
                                                            font.pixelSize: 12
                                                            color: HusTheme.Primary.colorTextSecondary
                                                        }

                                                        HusText {
                                                            id: afterText
                                                            Layout.fillWidth: true
                                                            text: modelData.after_preview || "未设置"
                                                            color: HusTheme.Primary.colorTextPrimary
                                                            wrapMode: Text.WrapAnywhere
                                                        }
                                                    }
                                                }
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                visible: Boolean(modelData.large)
                                                text: "内容较长，当前仅显示预览。"
                                                color: HusTheme.Primary.colorTextSecondary
                                                wrapMode: Text.Wrap
                                            }
                                        }
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    visible: Number(previewGroupCard.groupData.item_count || 0) === 0
                                    text: "该模块当前没有可应用变更。"
                                    color: HusTheme.Primary.colorTextSecondary
                                }
                            }
                        }
                    }

                    HusText {
                        Layout.fillWidth: true
                        visible: root.previewGroups.length === 0
                        text: "暂无预览结果"
                        color: HusTheme.Primary.colorTextSecondary
                    }
                }
            }
        }

        ScrollBar.vertical: HusScrollBar {}
    }

    SmoothWheelArea {
        anchors.fill: scroller
        target: scroller
        childTargets: [descriptionInput, personalityInput, scenarioInput, firstMessageInput, mesExampleInput, creatorNotesInput, personaDescriptionInput, personaPersonalityInput, personaScenarioInput, personaCreatorNotesInput, workshopNoteInput, databaseNotesInput, variableNotesInput, stageDescriptionInput, stageNotesInput, databaseTagDescriptionInput, databaseTagNotesInput, candidatePromptInput, candidateJsonInput]
    }
}
