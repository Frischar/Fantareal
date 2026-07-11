pragma ComponentBehavior: Bound

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
    property string sourceName: ""
    property string cardUid: ""
    property string cardName: ""
    property string tagsText: ""
    property string descriptionText: ""
    property string personalityText: ""
    property string scenarioText: ""
    property string firstMessageText: ""
    property string messageExampleText: ""
    property string creatorNotesText: ""
    property string creatorCommentText: ""
    property bool databaseEnabled: true
    property bool creativeWorkshopEnabled: true
    property bool openingEnabled: false
    property int dynamicSceneCount: 0

    property var personas: []
    property int selectedPersonaIndex: -1

    property var databaseConfig: ({
            "version": 1,
            "enabled": true,
            "role_source_mode": "auto",
            "roles": []
        })
    property int selectedDatabaseRoleIndex: -1
    property string databaseTab: "variables"
    property int selectedVariableIndex: -1
    property int selectedStageIndex: -1
    property int selectedSnapshotIndex: -1

    readonly property bool compactLayout: width < 980
    readonly property bool narrowLayout: width < 720

    function deepClone(value) {
        if (value === undefined || value === null) {
            return value;
        }
        try {
            return JSON.parse(JSON.stringify(value));
        } catch (error) {
            console.warn("[CardsPage] deep clone failed", error);
            return value;
        }
    }

    function asArray(value) {
        return Array.isArray(value) ? value : [];
    }

    function numberValue(value, fallback) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function stringList(value) {
        if (Array.isArray(value)) {
            return value.map(function (item) {
                return String(item || "").trim();
            }).filter(function (item) {
                return item.length > 0;
            });
        }
        return String(value || "").split(/[,，;\n]/).map(function (item) {
            return item.trim();
        }).filter(function (item) {
            return item.length > 0;
        });
    }

    function joinList(value) {
        return stringList(value).join(", ");
    }

    function uniqueStrings(value) {
        const result = [];
        const seen = {};
        const items = stringList(value);
        for (let i = 0; i < items.length; ++i) {
            const token = items[i].toLowerCase();
            if (!seen[token]) {
                seen[token] = true;
                result.push(items[i]);
            }
        }
        return result;
    }

    function slugify(value, fallback) {
        let text = String(value || "").trim().toLowerCase();
        text = text.replace(/\s+/g, "_");
        text = text.replace(/[^a-z0-9_\-]+/g, "");
        text = text.replace(/[_\-]{2,}/g, "_");
        text = text.replace(/^[_\-]+|[_\-]+$/g, "");
        return text.length > 0 ? text : String(fallback || "");
    }

    function stageLetter(index) {
        const letters = "abcdefghijklmnopqrstuvwxyz";
        const safeIndex = Math.max(1, Number(index || 1));
        const letter = letters[(safeIndex - 1) % letters.length];
        return letter + (safeIndex > letters.length ? Math.ceil(safeIndex / letters.length) : "");
    }

    function defaultStageKey(index) {
        return `stage_${stageLetter(index)}`;
    }

    function defaultStageName(index) {
        return `${stageLetter(index).toUpperCase()} 阶段`;
    }

    function normalizePersona(persona, index, keyHint) {
        const item = deepClone(persona || {}) || {};
        const key = String(item.key || item._key || keyHint || index + 1).trim() || String(index + 1);
        const name = String(item.name || "").trim();
        item.key = key;
        item.role_id = slugify(item.role_id || `current_card_${key}_${name}`, `current_card_role_${index + 1}`);
        item.name = name;
        item.aliases = uniqueStrings(item.aliases || []);
        item.tags = uniqueStrings(item.tags || []);
        item.description = String(item.description || "");
        item.personality = String(item.personality || "");
        item.scenario = String(item.scenario || "");
        item.creator_notes = String(item.creator_notes || "");
        delete item._key;
        return item;
    }

    function normalizePersonas(value) {
        const result = [];
        if (Array.isArray(value)) {
            for (let i = 0; i < value.length; ++i) {
                result.push(normalizePersona(value[i], i, ""));
            }
            return result;
        }
        const source = value && typeof value === "object" ? value : {};
        const keys = Object.keys(source);
        keys.sort(function (a, b) {
            const left = Number(a);
            const right = Number(b);
            if (!isNaN(left) && !isNaN(right)) {
                return left - right;
            }
            return String(a).localeCompare(String(b));
        });
        for (let i = 0; i < keys.length; ++i) {
            result.push(normalizePersona(source[keys[i]], i, keys[i]));
        }
        return result;
    }

    function normalizeRoleSourceMode(value) {
        const raw = String(value || "").trim().toLowerCase().replace(/-/g, "_");
        const aliases = {
            "main": "main_card",
            "single": "main_card",
            "single_role": "main_card",
            "card": "main_card",
            "persona": "personas_only",
            "personas": "personas_only",
            "multi": "personas_only",
            "multi_role": "personas_only",
            "narrator": "personas_only"
        };
        const mode = aliases[raw] || raw;
        return ["auto", "main_card", "personas_only"].indexOf(mode) >= 0 ? mode : "auto";
    }

    function normalizeRoleMode(value, role) {
        const raw = String(value || "").trim().toLowerCase().replace(/-/g, "_");
        const aliases = {
            "snapshot": "snapshot_only",
            "snapshot_fields": "snapshot_only",
            "note_only": "snapshot_only",
            "variable": "variables",
            "stage": "stages",
            "full_stage": "full",
            "off": "disabled",
            "none": "disabled",
            "disable": "disabled"
        };
        const mode = aliases[raw] || raw;
        if (["default", "variables", "stages", "snapshot_only", "full", "disabled"].indexOf(mode) >= 0) {
            return mode;
        }
        if (role && role.enabled === false) {
            return "disabled";
        }
        if (role && asArray(role.variables).length > 0 && asArray(role.stages).length > 0) {
            return "full";
        }
        if (role && asArray(role.snapshotFields).length > 0) {
            return "snapshot_only";
        }
        return "default";
    }

    function normalizeVariable(variable, index) {
        const item = deepClone(variable || {}) || {};
        const minimum = numberValue(item.min_value, 0);
        let maximum = numberValue(item.max_value, 100);
        if (maximum <= minimum) {
            maximum = minimum + 100;
        }
        const fallbackKey = `var_${index + 1}`;
        item.var_key = slugify(item.var_key || item.key, fallbackKey);
        item.var_name = String(item.var_name || item.label || item.var_key).trim() || item.var_key;
        item.enabled = item.enabled !== false;
        item.default_value = Math.min(Math.max(numberValue(item.default_value, minimum), minimum), maximum);
        item.min_value = minimum;
        item.max_value = maximum;
        item.delta_min = numberValue(item.delta_min, -5);
        item.delta_max = numberValue(item.delta_max, 5);
        item.display = item.display !== false;
        item.stage_relevant = item.stage_relevant !== false;
        item.instruction = String(item.instruction || "");
        return item;
    }

    function normalizeCondition(condition) {
        const item = deepClone(condition || {}) || {};
        const operation = String(item.op || ">=");
        item.var = slugify(item.var || item.field, "");
        item.op = [">", ">=", "<", "<=", "=", "!="].indexOf(operation) >= 0 ? operation : ">=";
        item.value = numberValue(item.value, 0);
        delete item.field;
        return item;
    }

    function normalizeStage(stage, roleId, index) {
        const item = deepClone(stage || {}) || {};
        item.stage_key = slugify(item.stage_key || item.key, defaultStageKey(index + 1));
        item.stage_name = String(item.stage_name || item.name || defaultStageName(index + 1)).trim() || defaultStageName(index + 1);
        item.enabled = item.enabled !== false;
        item.priority = numberValue(item.priority, (index + 1) * 10);
        item.condition_mode = String(item.condition_mode || "all") === "any" ? "any" : "all";
        item.conditions = asArray(item.conditions).map(function (condition) {
            return normalizeCondition(condition);
        }).filter(function (condition) {
            return condition.var.length > 0;
        });
        item.allow_regression = Boolean(item.allow_regression);
        item.confirm_turns = Math.max(1, Math.round(numberValue(item.confirm_turns, 1)));
        item.cooldown_turns = Math.max(0, Math.round(numberValue(item.cooldown_turns, 0)));
        item.activation_tag = `database.stage.${roleId}.${item.stage_key}`;
        return item;
    }

    function normalizeSnapshotField(field, index) {
        const item = deepClone(field || {}) || {};
        item.key = slugify(item.key || item.field_key, `snapshot_${index + 1}`);
        item.label = String(item.label || item.name || item.key).trim() || item.key;
        item.enabled = item.enabled !== false;
        item.display = item.display !== false;
        item.instruction = String(item.instruction || item.note || "根据本轮上下文生成该状态快照字段。");
        delete item.field_key;
        return item;
    }

    function normalizeDatabaseRole(role, index) {
        const item = deepClone(role || {}) || {};
        const roleName = String(item.role_name || item.name || `角色 ${index + 1}`).trim();
        const roleId = slugify(item.role_id || item.id || roleName, `role_${index + 1}`);
        const mode = normalizeRoleMode(item.mode || item.stateJournalMode, item);
        item.role_id = roleId;
        item.role_name = roleName || roleId;
        item.aliases = uniqueStrings(item.aliases || []);
        item.mode = mode;
        item.stateJournalMode = mode;
        item.enabled = mode !== "disabled";
        item.variables = asArray(item.variables).map(function (variable, variableIndex) {
            return normalizeVariable(variable, variableIndex);
        });
        item.stages = asArray(item.stages).map(function (stage, stageIndex) {
            return normalizeStage(stage, roleId, stageIndex);
        });
        item.snapshotFields = asArray(item.snapshotFields || item.snapshot_fields).map(function (field, fieldIndex) {
            return normalizeSnapshotField(field, fieldIndex);
        });
        item.initial_stage = slugify(item.initial_stage || (item.settings || {}).initial_stage, "stage_a");
        item.settings = item.settings && typeof item.settings === "object" ? deepClone(item.settings) : {
            "allow_regression": false,
            "confirm_turns": 1,
            "cooldown_turns": 2
        };
        if (item.variables.length > 0 || item.stages.length > 0 || item.snapshotFields.length > 0 || mode === "snapshot_only" || mode === "full") {
            item.has_state_journal_config = true;
        }
        delete item.snapshot_fields;
        return item;
    }

    function normalizeDatabaseConfig(value) {
        const source = deepClone(value || {}) || {};
        const result = source;
        result.version = Math.max(1, Math.round(numberValue(source.version, 1)));
        result.enabled = source.enabled === undefined ? true : source.enabled !== false;
        result.role_source_mode = normalizeRoleSourceMode(source.role_source_mode || source.roleSourceMode);
        result.roles = asArray(source.roles).map(function (role, index) {
            return normalizeDatabaseRole(role, index);
        });
        delete result.roleSourceMode;
        return result;
    }

    function markDirty() {
        if (initialized) {
            dirty = true;
        }
    }

    function updateTextField(key, value) {
        if (root[key] !== value) {
            root[key] = value;
            root.markDirty();
        }
    }

    function applyDraft(draft) {
        initialized = false;
        const source = draft || {};
        sourceName = source.source_name || "";
        cardUid = source.card_uid || "";
        cardName = source.name || "";
        tagsText = source.tagsText || "";
        descriptionText = source.description || "";
        personalityText = source.personality || "";
        scenarioText = source.scenario || "";
        firstMessageText = source.first_mes || "";
        messageExampleText = source.mes_example || "";
        creatorNotesText = source.creator_notes || "";
        creatorCommentText = source.creator_comment || "";
        creativeWorkshopEnabled = source.creativeWorkshopEnabled === undefined ? true : Boolean(source.creativeWorkshopEnabled);
        openingEnabled = Boolean(source.openingEnabled);
        dynamicSceneCount = Number(source.dynamicSceneCount || 0);
        personas = normalizePersonas(source.personas || []);
        selectedPersonaIndex = personas.length > 0 ? 0 : -1;
        const configSource = source.databaseConfig || {
            "version": 1,
            "enabled": source.databaseEnabled === undefined ? true : Boolean(source.databaseEnabled),
            "role_source_mode": "auto",
            "roles": []
        };
        databaseConfig = normalizeDatabaseConfig(configSource);
        databaseEnabled = source.databaseEnabled === undefined ? databaseConfig.enabled !== false : Boolean(source.databaseEnabled);
        databaseConfig.enabled = databaseEnabled;
        selectedDatabaseRoleIndex = databaseConfig.roles.length > 0 ? 0 : -1;
        databaseTab = "variables";
        resetDatabaseItemSelection();
        dirty = false;
        initialized = true;
    }

    function saveDraft() {
        const personasCopy = deepClone(normalizePersonas(personas));
        const databaseCopy = deepClone(normalizeDatabaseConfig(databaseConfig));
        databaseCopy.enabled = databaseEnabled;
        const result = FantarealBridge.saveCardDraft({
            "name": cardName,
            "tagsText": tagsText,
            "description": descriptionText,
            "personality": personalityText,
            "scenario": scenarioText,
            "first_mes": firstMessageText,
            "mes_example": messageExampleText,
            "creator_notes": creatorNotesText,
            "creator_comment": creatorCommentText,
            "databaseEnabled": databaseEnabled,
            "creativeWorkshopEnabled": creativeWorkshopEnabled,
            "openingEnabled": openingEnabled,
            "personas": personasCopy,
            "databaseConfig": databaseCopy
        });
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.cardDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function syncPersona() {
        if (root.dirty) {
            message.warning("请先保存角色卡，再同步人设。", 5000);
            return;
        }
        const result = FantarealBridge.syncCurrentCardToPersona();
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.cardDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function importRoleCard(path) {
        if (root.dirty) {
            message.warning("请先保存或还原当前编辑内容，再导入角色卡。", 5000);
            return;
        }
        const result = FantarealBridge.importRoleCardFile(path);
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.cardDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function currentPersona() {
        return selectedPersonaIndex >= 0 && selectedPersonaIndex < personas.length ? personas[selectedPersonaIndex] : null;
    }

    function personaTitle(persona, index) {
        const item = persona || {};
        return item.name || item.role_id || item.key || `多角色 ${index + 1}`;
    }

    function nextPersonaKey() {
        const used = {};
        for (let i = 0; i < personas.length; ++i) {
            used[String((personas[i] || {}).key || "")] = true;
        }
        let candidate = 1;
        while (used[String(candidate)]) {
            candidate += 1;
        }
        return String(candidate);
    }

    function addPersona() {
        const next = personas.length + 1;
        const key = nextPersonaKey();
        const items = deepClone(personas);
        items.push(normalizePersona({
            "key": key,
            "role_id": `current_card_role_${key}`,
            "name": `角色 ${next}`,
            "aliases": [],
            "tags": [],
            "description": "",
            "personality": "",
            "scenario": "",
            "creator_notes": ""
        }, next - 1, key));
        personas = items;
        selectedPersonaIndex = items.length - 1;
        markDirty();
    }

    function removePersona() {
        if (selectedPersonaIndex < 0 || selectedPersonaIndex >= personas.length) {
            return;
        }
        const items = deepClone(personas);
        items.splice(selectedPersonaIndex, 1);
        personas = items;
        selectedPersonaIndex = items.length === 0 ? -1 : Math.min(selectedPersonaIndex, items.length - 1);
        markDirty();
    }

    function updatePersonaField(field, value) {
        if (selectedPersonaIndex < 0 || selectedPersonaIndex >= personas.length) {
            return;
        }
        const items = deepClone(personas);
        if (field === "aliases" || field === "tags") {
            items[selectedPersonaIndex][field] = uniqueStrings(value);
        } else {
            items[selectedPersonaIndex][field] = value;
        }
        personas = items;
        markDirty();
    }

    function currentDatabaseRole() {
        const roles = asArray(databaseConfig.roles);
        return selectedDatabaseRoleIndex >= 0 && selectedDatabaseRoleIndex < roles.length ? roles[selectedDatabaseRoleIndex] : null;
    }

    function currentVariable() {
        const role = currentDatabaseRole();
        const items = role ? asArray(role.variables) : [];
        return selectedVariableIndex >= 0 && selectedVariableIndex < items.length ? items[selectedVariableIndex] : null;
    }

    function currentStage() {
        const role = currentDatabaseRole();
        const items = role ? asArray(role.stages) : [];
        return selectedStageIndex >= 0 && selectedStageIndex < items.length ? items[selectedStageIndex] : null;
    }

    function currentSnapshotField() {
        const role = currentDatabaseRole();
        const items = role ? asArray(role.snapshotFields) : [];
        return selectedSnapshotIndex >= 0 && selectedSnapshotIndex < items.length ? items[selectedSnapshotIndex] : null;
    }

    function databaseRoleTitle(role, index) {
        const item = role || {};
        return item.role_name || item.role_id || `数据库角色 ${index + 1}`;
    }

    function roleModeLabel(mode) {
        const labels = {
            "default": "默认",
            "snapshot_only": "仅状态记录",
            "full": "完整数据库",
            "disabled": "不记录"
        };
        return labels[normalizeRoleMode(mode, {})] || "默认";
    }

    function roleSourceDescription(mode) {
        const descriptions = {
            "auto": "自动识别主卡和有内容的多角色；空占位角色不会加入数据库列表。",
            "main_card": "把主卡作为唯一角色，适合普通单角色卡。",
            "personas_only": "把主卡视为旁白，只展开有内容的多角色。"
        };
        return descriptions[normalizeRoleSourceMode(mode)] || descriptions.auto;
    }

    function setDatabaseEnabled(enabled) {
        const config = deepClone(databaseConfig);
        config.enabled = Boolean(enabled);
        databaseConfig = config;
        databaseEnabled = Boolean(enabled);
        markDirty();
    }

    function setRoleSourceMode(mode) {
        const config = deepClone(databaseConfig);
        config.role_source_mode = normalizeRoleSourceMode(mode);
        databaseConfig = config;
        syncDatabaseRoles();
    }

    function personaIsPlaceholder(persona) {
        const item = persona || {};
        const name = String(item.name || "").trim();
        const placeholder = /^\d+$/.test(name) || /^role\s*[a-z0-9]+$/i.test(name) || /^角色\s*[a-z0-9\d]+$/i.test(name);
        const hasContent = [item.description, item.personality, item.scenario, item.creator_notes].some(function (value) {
            return String(value || "").trim().length > 0;
        });
        return placeholder && !hasContent;
    }

    function mainRoleSeed() {
        const name = String(cardName || "主卡角色").trim() || "主卡角色";
        return {
            "role_id": slugify(name, "main_card"),
            "role_name": name,
            "aliases": [],
            "mode": "default",
            "stateJournalMode": "default",
            "enabled": true,
            "source": "main_card",
            "source_type": "main_card",
            "display_policy": "show",
            "variables": [],
            "stages": [],
            "snapshotFields": []
        };
    }

    function personaRoleSeed(persona, index) {
        const item = persona || {};
        return {
            "role_id": slugify(item.role_id || `current_card_role_${index + 1}`, `current_card_role_${index + 1}`),
            "role_name": item.name || `角色 ${index + 1}`,
            "aliases": uniqueStrings([item.key].concat(asArray(item.aliases))),
            "mode": "default",
            "stateJournalMode": "default",
            "enabled": true,
            "source": "persona",
            "source_type": "multi_role_slot",
            "has_state_journal_config": false,
            "is_empty_slot": false,
            "display_policy": "show",
            "variables": [],
            "stages": [],
            "snapshotFields": []
        };
    }

    function desiredDatabaseRoleSeeds() {
        const mode = normalizeRoleSourceMode(databaseConfig.role_source_mode);
        const personaRoles = [];
        for (let i = 0; i < personas.length; ++i) {
            if (!personaIsPlaceholder(personas[i])) {
                personaRoles.push(personaRoleSeed(personas[i], i));
            }
        }
        if (mode === "main_card") {
            return [mainRoleSeed()];
        }
        if (mode === "personas_only") {
            return personaRoles;
        }
        return [mainRoleSeed()].concat(personaRoles);
    }

    function roleHasConfig(role) {
        const item = role || {};
        return asArray(item.variables).length > 0 || asArray(item.stages).length > 0 || asArray(item.snapshotFields).length > 0 || item.has_state_journal_config === true;
    }

    function syncDatabaseRoles() {
        const config = deepClone(databaseConfig);
        const existingRoles = asArray(config.roles);
        const existingById = {};
        for (let i = 0; i < existingRoles.length; ++i) {
            const normalized = normalizeDatabaseRole(existingRoles[i], i);
            existingById[normalized.role_id] = normalized;
        }
        const oldSelectedRole = currentDatabaseRole();
        const oldSelectedId = oldSelectedRole ? oldSelectedRole.role_id : "";
        const desired = desiredDatabaseRoleSeeds();
        const nextRoles = [];
        const desiredIds = {};
        for (let i = 0; i < desired.length; ++i) {
            const seed = normalizeDatabaseRole(desired[i], i);
            desiredIds[seed.role_id] = true;
            if (existingById[seed.role_id]) {
                const merged = deepClone(existingById[seed.role_id]);
                merged.role_name = seed.role_name;
                merged.aliases = uniqueStrings(asArray(merged.aliases).concat(seed.aliases));
                merged.source = seed.source;
                merged.source_type = seed.source_type;
                merged.is_empty_slot = false;
                merged.display_policy = "show";
                nextRoles.push(normalizeDatabaseRole(merged, nextRoles.length));
            } else {
                nextRoles.push(seed);
            }
        }
        for (let i = 0; i < existingRoles.length; ++i) {
            const oldRole = normalizeDatabaseRole(existingRoles[i], i);
            const managedSource = oldRole.source === "main_card" || oldRole.source === "persona";
            if (!desiredIds[oldRole.role_id] && !managedSource && roleHasConfig(oldRole)) {
                nextRoles.push(oldRole);
            }
        }
        config.roles = nextRoles;
        databaseConfig = normalizeDatabaseConfig(config);
        selectedDatabaseRoleIndex = -1;
        for (let i = 0; i < nextRoles.length; ++i) {
            if (nextRoles[i].role_id === oldSelectedId) {
                selectedDatabaseRoleIndex = i;
                break;
            }
        }
        if (selectedDatabaseRoleIndex < 0 && nextRoles.length > 0) {
            selectedDatabaseRoleIndex = 0;
        }
        resetDatabaseItemSelection();
        markDirty();
    }

    function selectDatabaseRole(index) {
        selectedDatabaseRoleIndex = index;
        resetDatabaseItemSelection();
    }

    function resetDatabaseItemSelection() {
        selectedVariableIndex = -1;
        selectedStageIndex = -1;
        selectedSnapshotIndex = -1;
        const role = currentDatabaseRole();
        if (!role) {
            return;
        }
        if (asArray(role.variables).length > 0) {
            selectedVariableIndex = 0;
        }
        if (asArray(role.stages).length > 0) {
            selectedStageIndex = 0;
        }
        if (asArray(role.snapshotFields).length > 0) {
            selectedSnapshotIndex = 0;
        }
    }

    function setDatabaseTab(tab) {
        databaseTab = tab;
    }

    function updateDatabaseRoleMode(mode) {
        if (selectedDatabaseRoleIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const role = config.roles[selectedDatabaseRoleIndex];
        const safeMode = normalizeRoleMode(mode, role);
        role.mode = safeMode;
        role.stateJournalMode = safeMode;
        role.enabled = safeMode !== "disabled";
        if (safeMode === "snapshot_only" || safeMode === "full") {
            role.has_state_journal_config = true;
        }
        databaseConfig = config;
        markDirty();
    }

    function roleCollectionName(tab) {
        if (tab === "stages") {
            return "stages";
        }
        if (tab === "snapshot") {
            return "snapshotFields";
        }
        return "variables";
    }

    function updateRoleItem(collection, index, field, value) {
        if (selectedDatabaseRoleIndex < 0 || index < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const role = config.roles[selectedDatabaseRoleIndex];
        const items = asArray(role[collection]);
        if (index >= items.length) {
            return;
        }
        if (items[index][field] === value) {
            return;
        }
        items[index][field] = value;
        if (collection === "stages" && field === "stage_key") {
            items[index].activation_tag = `database.stage.${role.role_id}.${value}`;
        }
        role[collection] = items;
        role.has_state_journal_config = true;
        databaseConfig = config;
        markDirty();
    }

    function addVariable() {
        if (selectedDatabaseRoleIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const role = config.roles[selectedDatabaseRoleIndex];
        const items = asArray(role.variables);
        const next = items.length + 1;
        items.push(normalizeVariable({
            "var_key": `var_${next}`,
            "var_name": "新变量",
            "enabled": true,
            "default_value": 0,
            "min_value": 0,
            "max_value": 100,
            "delta_min": -2,
            "delta_max": 2,
            "display": true,
            "stage_relevant": true,
            "instruction": ""
        }, items.length));
        role.variables = items;
        role.has_state_journal_config = true;
        databaseConfig = config;
        selectedVariableIndex = items.length - 1;
        markDirty();
    }

    function removeVariable() {
        if (selectedDatabaseRoleIndex < 0 || selectedVariableIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const items = asArray(config.roles[selectedDatabaseRoleIndex].variables);
        items.splice(selectedVariableIndex, 1);
        config.roles[selectedDatabaseRoleIndex].variables = items;
        databaseConfig = config;
        selectedVariableIndex = items.length === 0 ? -1 : Math.min(selectedVariableIndex, items.length - 1);
        markDirty();
    }

    function addStage() {
        if (selectedDatabaseRoleIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const role = config.roles[selectedDatabaseRoleIndex];
        const items = asArray(role.stages);
        const next = items.length + 1;
        items.push(normalizeStage({
            "stage_key": defaultStageKey(next),
            "stage_name": defaultStageName(next),
            "enabled": true,
            "priority": next * 10,
            "condition_mode": "all",
            "conditions": [],
            "allow_regression": false,
            "confirm_turns": 1,
            "cooldown_turns": 0
        }, role.role_id, items.length));
        role.stages = items;
        role.has_state_journal_config = true;
        databaseConfig = config;
        selectedStageIndex = items.length - 1;
        markDirty();
    }

    function removeStage() {
        if (selectedDatabaseRoleIndex < 0 || selectedStageIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const items = asArray(config.roles[selectedDatabaseRoleIndex].stages);
        items.splice(selectedStageIndex, 1);
        config.roles[selectedDatabaseRoleIndex].stages = items;
        databaseConfig = config;
        selectedStageIndex = items.length === 0 ? -1 : Math.min(selectedStageIndex, items.length - 1);
        markDirty();
    }

    function addSnapshotField() {
        if (selectedDatabaseRoleIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const role = config.roles[selectedDatabaseRoleIndex];
        const items = asArray(role.snapshotFields);
        const next = items.length + 1;
        items.push(normalizeSnapshotField({
            "key": `snapshot_${next}`,
            "label": "新快照字段",
            "enabled": true,
            "display": true,
            "instruction": "根据本轮上下文生成该状态快照字段。"
        }, items.length));
        role.snapshotFields = items;
        role.has_state_journal_config = true;
        databaseConfig = config;
        selectedSnapshotIndex = items.length - 1;
        markDirty();
    }

    function removeSnapshotField() {
        if (selectedDatabaseRoleIndex < 0 || selectedSnapshotIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const items = asArray(config.roles[selectedDatabaseRoleIndex].snapshotFields);
        items.splice(selectedSnapshotIndex, 1);
        config.roles[selectedDatabaseRoleIndex].snapshotFields = items;
        databaseConfig = config;
        selectedSnapshotIndex = items.length === 0 ? -1 : Math.min(selectedSnapshotIndex, items.length - 1);
        markDirty();
    }

    function addStageCondition() {
        if (selectedDatabaseRoleIndex < 0 || selectedStageIndex < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const role = config.roles[selectedDatabaseRoleIndex];
        const stage = role.stages[selectedStageIndex];
        const variables = asArray(role.variables);
        const conditions = asArray(stage.conditions);
        conditions.push({
            "var": variables.length > 0 ? variables[0].var_key : "",
            "op": ">=",
            "value": 0
        });
        stage.conditions = conditions;
        role.has_state_journal_config = true;
        databaseConfig = config;
        markDirty();
    }

    function updateStageCondition(index, field, value) {
        if (selectedDatabaseRoleIndex < 0 || selectedStageIndex < 0 || index < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const conditions = asArray(config.roles[selectedDatabaseRoleIndex].stages[selectedStageIndex].conditions);
        if (index >= conditions.length) {
            return;
        }
        if (conditions[index][field] === value) {
            return;
        }
        conditions[index][field] = value;
        config.roles[selectedDatabaseRoleIndex].stages[selectedStageIndex].conditions = conditions;
        databaseConfig = config;
        markDirty();
    }

    function removeStageCondition(index) {
        if (selectedDatabaseRoleIndex < 0 || selectedStageIndex < 0 || index < 0) {
            return;
        }
        const config = deepClone(databaseConfig);
        const conditions = asArray(config.roles[selectedDatabaseRoleIndex].stages[selectedStageIndex].conditions);
        if (index >= conditions.length) {
            return;
        }
        conditions.splice(index, 1);
        config.roles[selectedDatabaseRoleIndex].stages[selectedStageIndex].conditions = conditions;
        databaseConfig = config;
        markDirty();
    }

    Component.onCompleted: applyDraft(FantarealBridge.cardDraft)

    FileDialog {
        id: roleCardImportDialog
        title: "导入角色卡 JSON"
        nameFilters: ["JSON 文件 (*.json)", "所有文件 (*)"]
        onAccepted: root.importRoleCard(selectedFile.toString())
    }

    Connections {
        target: FantarealBridge

        function onScanChanged() {
            if (!root.dirty) {
                root.applyDraft(FantarealBridge.cardDraft);
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
        contentHeight: pageColumn.implicitHeight + 56
        clip: true

        ColumnLayout {
            id: pageColumn
            width: Math.max(320, Math.min(scroller.width - (root.narrowLayout ? 24 : 64), 1320))
            x: Math.max(12, (scroller.width - width) / 2)
            y: root.narrowLayout ? 20 : 32
            spacing: 20

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    HusText {
                        Layout.fillWidth: true
                        text: "角色卡"
                        font.pixelSize: root.narrowLayout ? 24 : 28
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    HusText {
                        Layout.fillWidth: true
                        text: root.sourceName ? `${root.sourceName}${root.cardUid ? ` · ${root.cardUid}` : ""}` : "编辑当前角色卡"
                        font.pixelSize: 12
                        color: HusTheme.Primary.colorTextSecondary
                        elide: Text.ElideMiddle
                    }
                }

                HusTag {
                    visible: root.dirty
                    text: "未保存"
                    tagState: HusTag.State_Warning
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8

                HusButton {
                    text: "刷新"
                    onClicked: FantarealBridge.refreshLegacyScan()
                }

                HusButton {
                    text: "导入"
                    type: HusButton.Type_Filled
                    enabled: !root.dirty
                    onClicked: roleCardImportDialog.open()
                }

                HusButton {
                    text: "还原"
                    enabled: root.dirty
                    onClicked: root.applyDraft(FantarealBridge.cardDraft)
                }

                HusButton {
                    text: "同步人设"
                    type: HusButton.Type_Filled
                    enabled: !root.dirty
                    onClicked: root.syncPersona()
                }

                HusButton {
                    text: "保存"
                    type: HusButton.Type_Primary
                    enabled: root.dirty
                    onClicked: root.saveDraft()
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: basicContent.implicitHeight + 44
                accentColor: Global.accentViolet

                ColumnLayout {
                    id: basicContent
                    anchors.fill: parent
                    anchors.margins: root.narrowLayout ? 16 : 22
                    spacing: 18

                    HusText {
                        Layout.fillWidth: true
                        text: "主卡基础编辑"
                        font.pixelSize: 21
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.compactLayout ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "角色名称"

                            HusInput {
                                width: parent.width
                                text: root.cardName
                                placeholderText: "主卡角色名称"
                                clearEnabled: "active"
                                iconSource: HusIcon.UserOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.cardName = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "标签"

                            HusInput {
                                width: parent.width
                                text: root.tagsText
                                placeholderText: "幻想, 群像, 长篇"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.tagsText = text;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.compactLayout ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "演出工坊"

                            HusSwitch {
                                checked: root.creativeWorkshopEnabled
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.creativeWorkshopEnabled = checked;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "开场演出"
                            description: root.dynamicSceneCount > 0 ? `当前有 ${root.dynamicSceneCount} 个动态场景` : ""

                            HusSwitch {
                                checked: root.openingEnabled
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.openingEnabled = checked;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 1
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorSplit, 0.42)
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "角色描述（description）"

                        HusTextArea {
                            id: descriptionInput
                            width: parent.width
                            minRows: 4
                            maxRows: 8
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.descriptionText
                            placeholderText: "角色定义、外观与背景"
                            onTextChanged: {
                                if (activeFocus) {
                                    root.updateTextField("descriptionText", text);
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "性格（personality）"

                        HusTextArea {
                            id: personalityInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.personalityText
                            placeholderText: "性格、语气与行为偏好"
                            onTextChanged: {
                                if (activeFocus) {
                                    root.updateTextField("personalityText", text);
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
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
                                if (activeFocus) {
                                    root.updateTextField("scenarioText", text);
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "首条消息（first_mes）"

                        HusTextArea {
                            id: firstMessageInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.firstMessageText
                            placeholderText: "角色的第一条开场消息"
                            onTextChanged: {
                                if (activeFocus) {
                                    root.updateTextField("firstMessageText", text);
                                }
                            }
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "对话示例（mes_example）"

                        HusTextArea {
                            id: messageExampleInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.messageExampleText
                            placeholderText: "示例对话"
                            onTextChanged: {
                                if (activeFocus) {
                                    root.updateTextField("messageExampleText", text);
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.compactLayout ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "作者备注（creator_notes）"

                            HusTextArea {
                                id: creatorNotesInput
                                width: parent.width
                                minRows: 3
                                maxRows: 6
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.creatorNotesText
                                placeholderText: "隐藏纪律、写作边界与维护说明"
                                onTextChanged: {
                                    if (activeFocus) {
                                        root.updateTextField("creatorNotesText", text);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "作者评论（creator_comment）"

                            HusTextArea {
                                id: creatorCommentInput
                                width: parent.width
                                minRows: 3
                                maxRows: 6
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.creatorCommentText
                                placeholderText: "作者评论或导入说明"
                                onTextChanged: {
                                    if (activeFocus) {
                                        root.updateTextField("creatorCommentText", text);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: personaContent.implicitHeight + 44
                accentColor: Global.accentCyan

                ColumnLayout {
                    id: personaContent
                    anchors.fill: parent
                    anchors.margins: root.narrowLayout ? 16 : 22
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        HusText {
                            Layout.fillWidth: true
                            text: "多角色"
                            font.pixelSize: 21
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.personas.length} 个`
                            tagState: root.personas.length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }
                    }

                    HusText {
                        Layout.fillWidth: true
                        text: "用于维护主卡中的独立角色槽位。这里是角色资料编辑，不是写卡器。"
                        color: HusTheme.Primary.colorTextSecondary
                        wrapMode: Text.Wrap
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        HusButton {
                            text: "新增角色"
                            type: HusButton.Type_Primary
                            onClicked: root.addPersona()
                        }

                        HusButton {
                            text: "删除当前"
                            type: HusButton.Type_Outlined
                            enabled: root.selectedPersonaIndex >= 0
                            onClicked: root.removePersona()
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.compactLayout ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredWidth: root.compactLayout ? -1 : 300
                            Layout.preferredHeight: 320
                            radius: 6
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.34)

                            HusEmpty {
                                anchors.centerIn: parent
                                width: 240
                                height: 150
                                visible: root.personas.length === 0
                                description: "暂无多角色，新增后可编辑详细资料"
                                imageStyle: HusEmpty.Style_Simple
                            }

                            ListView {
                                id: personaList
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 6
                                clip: true
                                visible: root.personas.length > 0
                                model: root.personas

                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index

                                    width: ListView.view.width
                                    height: 62
                                    radius: 5
                                    color: HusThemeFunctions.alpha(index === root.selectedPersonaIndex ? Global.accentCyan : HusTheme.Primary.colorBgBase, index === root.selectedPersonaIndex ? 0.24 : 0.08)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(index === root.selectedPersonaIndex ? Global.accentCyan : HusTheme.Primary.colorBorder, 0.34)

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 9
                                        spacing: 3

                                        HusText {
                                            Layout.fillWidth: true
                                            text: root.personaTitle(modelData, index)
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                            elide: Text.ElideRight
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: `${modelData.key || "-"} · ${modelData.role_id || "-"}`
                                            font.pixelSize: 11
                                            color: HusTheme.Primary.colorTextSecondary
                                            elide: Text.ElideMiddle
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectedPersonaIndex = index
                                    }
                                }

                                ScrollBar.vertical: HusScrollBar {}
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 14
                            visible: root.currentPersona() !== null

                            GridLayout {
                                Layout.fillWidth: true
                                columns: root.narrowLayout ? 1 : 2
                                columnSpacing: 14
                                rowSpacing: 14

                                SettingField {
                                    title: "槽位键（key）"

                                    HusInput {
                                        width: parent.width
                                        text: root.currentPersona() ? root.currentPersona().key : ""
                                        placeholderText: "例如：2"
                                        clearEnabled: "active"
                                        onTextEdited: root.updatePersonaField("key", text)
                                    }
                                }

                                SettingField {
                                    title: "角色标识（role_id）"

                                    HusInput {
                                        width: parent.width
                                        text: root.currentPersona() ? root.currentPersona().role_id : ""
                                        placeholderText: "例如：shen_qixue"
                                        clearEnabled: "active"
                                        onTextEdited: root.updatePersonaField("role_id", text)
                                    }
                                }

                                SettingField {
                                    title: "名称（name）"

                                    HusInput {
                                        width: parent.width
                                        text: root.currentPersona() ? root.currentPersona().name : ""
                                        placeholderText: "角色名称"
                                        clearEnabled: "active"
                                        onTextEdited: root.updatePersonaField("name", text)
                                    }
                                }

                                SettingField {
                                    title: "别名（aliases）"

                                    HusInput {
                                        width: parent.width
                                        text: root.currentPersona() ? root.joinList(root.currentPersona().aliases) : ""
                                        placeholderText: "用逗号分隔"
                                        clearEnabled: "active"
                                        onTextEdited: root.updatePersonaField("aliases", text)
                                    }
                                }

                                SettingField {
                                    Layout.columnSpan: root.narrowLayout ? 1 : 2
                                    title: "标签（tags）"

                                    HusInput {
                                        width: parent.width
                                        text: root.currentPersona() ? root.joinList(root.currentPersona().tags) : ""
                                        placeholderText: "配角, 群像, 阶段"
                                        clearEnabled: "active"
                                        onTextEdited: root.updatePersonaField("tags", text)
                                    }
                                }
                            }

                            SettingField {
                                Layout.fillWidth: true
                                title: "角色描述（description）"

                                HusTextArea {
                                    id: personaDescriptionInput
                                    width: parent.width
                                    minRows: 3
                                    maxRows: 6
                                    maxLength: 12000
                                    autoSize: true
                                    resizable: true
                                    text: root.currentPersona() ? root.currentPersona().description : ""
                                    placeholderText: "角色定义、外观与背景"
                                    onTextChanged: {
                                        if (activeFocus) {
                                            root.updatePersonaField("description", text);
                                        }
                                    }
                                }
                            }

                            SettingField {
                                Layout.fillWidth: true
                                title: "性格（personality）"

                                HusTextArea {
                                    id: personaPersonalityInput
                                    width: parent.width
                                    minRows: 3
                                    maxRows: 6
                                    maxLength: 12000
                                    autoSize: true
                                    resizable: true
                                    text: root.currentPersona() ? root.currentPersona().personality : ""
                                    placeholderText: "性格、语气与行为偏好"
                                    onTextChanged: {
                                        if (activeFocus) {
                                            root.updatePersonaField("personality", text);
                                        }
                                    }
                                }
                            }

                            SettingField {
                                Layout.fillWidth: true
                                title: "场景（scenario）"

                                HusTextArea {
                                    id: personaScenarioInput
                                    width: parent.width
                                    minRows: 3
                                    maxRows: 6
                                    maxLength: 12000
                                    autoSize: true
                                    resizable: true
                                    text: root.currentPersona() ? root.currentPersona().scenario : ""
                                    placeholderText: "该角色的场景与互动前提"
                                    onTextChanged: {
                                        if (activeFocus) {
                                            root.updatePersonaField("scenario", text);
                                        }
                                    }
                                }
                            }

                            SettingField {
                                Layout.fillWidth: true
                                title: "作者备注（creator_notes）"

                                HusTextArea {
                                    id: personaCreatorNotesInput
                                    width: parent.width
                                    minRows: 3
                                    maxRows: 6
                                    maxLength: 12000
                                    autoSize: true
                                    resizable: true
                                    text: root.currentPersona() ? root.currentPersona().creator_notes : ""
                                    placeholderText: "该角色的隐藏纪律与维护说明"
                                    onTextChanged: {
                                        if (activeFocus) {
                                            root.updatePersonaField("creator_notes", text);
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
                Layout.preferredHeight: databaseContent.implicitHeight + 44
                accentColor: Global.accentBlue

                ColumnLayout {
                    id: databaseContent
                    anchors.fill: parent
                    anchors.margins: root.narrowLayout ? 16 : 22
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3

                            HusText {
                                Layout.fillWidth: true
                                text: "数据库配置"
                                font.pixelSize: 21
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: "按角色维护状态记录、变量、阶段规则与状态快照字段。"
                                color: HusTheme.Primary.colorTextSecondary
                                wrapMode: Text.Wrap
                            }
                        }

                        HusSwitch {
                            checked: root.databaseEnabled
                            checkedText: "开启"
                            uncheckedText: "关闭"
                            onToggled: root.setDatabaseEnabled(checked)
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "角色来源"
                        description: root.roleSourceDescription(root.databaseConfig.role_source_mode)

                        Flow {
                            width: parent.width
                            spacing: 8

                            HusButton {
                                text: "自动识别"
                                type: root.databaseConfig.role_source_mode === "auto" ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.setRoleSourceMode("auto")
                            }

                            HusButton {
                                text: "主卡就是角色"
                                type: root.databaseConfig.role_source_mode === "main_card" ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.setRoleSourceMode("main_card")
                            }

                            HusButton {
                                text: "主卡旁白，多角色展开"
                                type: root.databaseConfig.role_source_mode === "personas_only" ? HusButton.Type_Primary : HusButton.Type_Outlined
                                onClicked: root.setRoleSourceMode("personas_only")
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        HusTag {
                            text: `${root.asArray(root.databaseConfig.roles).length} 个数据库角色`
                            tagState: root.asArray(root.databaseConfig.roles).length > 0 ? HusTag.State_Success : HusTag.State_Default
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        HusButton {
                            text: "同步角色列表"
                            type: HusButton.Type_Filled
                            onClicked: root.syncDatabaseRoles()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: databaseDisabledText.implicitHeight + 28
                        radius: 6
                        visible: !root.databaseEnabled
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.34)

                        HusText {
                            id: databaseDisabledText
                            anchors.fill: parent
                            anchors.margins: 14
                            text: "数据库已关闭。角色、变量、阶段和快照草稿仍会保留，重新开启后可继续编辑。"
                            color: HusTheme.Primary.colorTextSecondary
                            wrapMode: Text.Wrap
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.databaseEnabled
                        columns: root.compactLayout ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredWidth: root.compactLayout ? -1 : 310
                            Layout.preferredHeight: 430
                            radius: 6
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.34)

                            HusEmpty {
                                anchors.centerIn: parent
                                width: 260
                                height: 170
                                visible: root.asArray(root.databaseConfig.roles).length === 0
                                description: "暂无数据库角色，请同步主卡与多角色"
                                imageStyle: HusEmpty.Style_Simple
                            }

                            ListView {
                                id: databaseRoleList
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 6
                                clip: true
                                visible: root.asArray(root.databaseConfig.roles).length > 0
                                model: root.asArray(root.databaseConfig.roles)

                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index

                                    width: ListView.view.width
                                    height: 82
                                    radius: 5
                                    color: HusThemeFunctions.alpha(index === root.selectedDatabaseRoleIndex ? Global.accentBlue : HusTheme.Primary.colorBgBase, index === root.selectedDatabaseRoleIndex ? 0.24 : 0.08)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(index === root.selectedDatabaseRoleIndex ? Global.accentBlue : HusTheme.Primary.colorBorder, 0.34)

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 9
                                        spacing: 4

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            HusText {
                                                Layout.fillWidth: true
                                                text: root.databaseRoleTitle(modelData, index)
                                                font.weight: Font.DemiBold
                                                color: HusTheme.Primary.colorTextPrimary
                                                elide: Text.ElideRight
                                            }

                                            HusTag {
                                                text: root.roleModeLabel(modelData.mode)
                                                tagState: modelData.mode === "disabled" ? HusTag.State_Warning : HusTag.State_Default
                                            }
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: modelData.role_id || "-"
                                            font.pixelSize: 11
                                            color: HusTheme.Primary.colorTextSecondary
                                            elide: Text.ElideMiddle
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: `变量 ${root.asArray(modelData.variables).length} · 阶段 ${root.asArray(modelData.stages).length} · 快照 ${root.asArray(modelData.snapshotFields).length}`
                                            font.pixelSize: 11
                                            color: HusTheme.Primary.colorTextTertiary
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectDatabaseRole(index)
                                    }
                                }

                                ScrollBar.vertical: HusScrollBar {}
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 14
                            visible: root.currentDatabaseRole() !== null

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    HusText {
                                        Layout.fillWidth: true
                                        text: root.currentDatabaseRole() ? root.currentDatabaseRole().role_name : ""
                                        font.pixelSize: 19
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                        elide: Text.ElideRight
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        text: root.currentDatabaseRole() ? root.currentDatabaseRole().role_id : ""
                                        font.pixelSize: 11
                                        color: HusTheme.Primary.colorTextSecondary
                                        elide: Text.ElideMiddle
                                    }
                                }
                            }

                            SettingField {
                                Layout.fillWidth: true
                                title: "记录模式"

                                Flow {
                                    width: parent.width
                                    spacing: 8

                                    Repeater {
                                        model: [
                                            {
                                                "label": "默认",
                                                "value": "default"
                                            },
                                            {
                                                "label": "变量与快照",
                                                "value": "variables"
                                            },
                                            {
                                                "label": "阶段与快照",
                                                "value": "stages"
                                            },
                                            {
                                                "label": "仅状态记录",
                                                "value": "snapshot_only"
                                            },
                                            {
                                                "label": "完整数据库",
                                                "value": "full"
                                            },
                                            {
                                                "label": "不记录",
                                                "value": "disabled"
                                            }
                                        ]

                                        delegate: HusButton {
                                            required property var modelData

                                            text: modelData.label
                                            type: root.currentDatabaseRole() && root.currentDatabaseRole().mode === modelData.value ? HusButton.Type_Primary : HusButton.Type_Outlined
                                            onClicked: root.updateDatabaseRoleMode(modelData.value)
                                        }
                                    }
                                }
                            }

                            HusSegmented {
                                Layout.fillWidth: true
                                options: [
                                    {
                                        "label": "变量表",
                                        "value": "variables"
                                    },
                                    {
                                        "label": "阶段规则",
                                        "value": "stages"
                                    },
                                    {
                                        "label": "状态快照字段",
                                        "value": "snapshot"
                                    }
                                ]
                                currentIndex: root.databaseTab === "stages" ? 1 : (root.databaseTab === "snapshot" ? 2 : 0)
                                onCurrentIndexChanged: root.setDatabaseTab(currentIndex === 1 ? "stages" : (currentIndex === 2 ? "snapshot" : "variables"))
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                visible: root.databaseTab === "variables"

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    HusText {
                                        Layout.fillWidth: true
                                        text: "变量表"
                                        font.pixelSize: 17
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                    }

                                    HusButton {
                                        text: "新增"
                                        type: HusButton.Type_Primary
                                        onClicked: root.addVariable()
                                    }

                                    HusButton {
                                        text: "删除"
                                        type: HusButton.Type_Outlined
                                        enabled: root.selectedVariableIndex >= 0
                                        onClicked: root.removeVariable()
                                    }
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 7

                                    Repeater {
                                        model: root.currentDatabaseRole() ? root.asArray(root.currentDatabaseRole().variables) : []

                                        delegate: HusButton {
                                            required property var modelData
                                            required property int index

                                            text: modelData.var_name || modelData.var_key || `变量 ${index + 1}`
                                            type: index === root.selectedVariableIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                            onClicked: root.selectedVariableIndex = index
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 58
                                    radius: 6
                                    visible: root.currentDatabaseRole() && root.asArray(root.currentDatabaseRole().variables).length === 0
                                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.34)

                                    HusText {
                                        anchors.centerIn: parent
                                        text: "暂无变量。完整数据库模式可在这里新增变量。"
                                        color: HusTheme.Primary.colorTextSecondary
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 14
                                    visible: root.currentDatabaseRole() && root.selectedVariableIndex >= 0 && root.selectedVariableIndex < root.asArray(root.currentDatabaseRole().variables).length

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: root.narrowLayout ? 1 : 2
                                        columnSpacing: 14
                                        rowSpacing: 14

                                        SettingField {
                                            title: "启用（enabled）"

                                            HusSwitch {
                                                checked: root.currentVariable() ? root.currentVariable().enabled !== false : false
                                                checkedText: "开启"
                                                uncheckedText: "关闭"
                                                onToggled: root.updateRoleItem("variables", root.selectedVariableIndex, "enabled", checked)
                                            }
                                        }

                                        SettingField {
                                            title: "显示（display）"

                                            HusSwitch {
                                                checked: root.currentVariable() ? root.currentVariable().display !== false : false
                                                checkedText: "显示"
                                                uncheckedText: "隐藏"
                                                onToggled: root.updateRoleItem("variables", root.selectedVariableIndex, "display", checked)
                                            }
                                        }

                                        SettingField {
                                            title: "变量键（var_key）"

                                            HusInput {
                                                width: parent.width
                                                text: root.currentVariable() ? root.currentVariable().var_key : ""
                                                placeholderText: "例如：trust"
                                                clearEnabled: "active"
                                                onTextEdited: root.updateRoleItem("variables", root.selectedVariableIndex, "var_key", text)
                                            }
                                        }

                                        SettingField {
                                            title: "变量名称（var_name）"

                                            HusInput {
                                                width: parent.width
                                                text: root.currentVariable() ? root.currentVariable().var_name : ""
                                                placeholderText: "例如：信任"
                                                clearEnabled: "active"
                                                onTextEdited: root.updateRoleItem("variables", root.selectedVariableIndex, "var_name", text)
                                            }
                                        }

                                        SettingField {
                                            title: "默认值（default_value）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentVariable() ? root.numberValue(root.currentVariable().default_value, 0) : 0
                                                min: -1000000
                                                max: 1000000
                                                step: 1
                                                precision: 2
                                                onValueModified: root.updateRoleItem("variables", root.selectedVariableIndex, "default_value", value)
                                            }
                                        }

                                        SettingField {
                                            title: "参与阶段判断（stage_relevant）"

                                            HusSwitch {
                                                checked: root.currentVariable() ? root.currentVariable().stage_relevant !== false : false
                                                checkedText: "参与"
                                                uncheckedText: "不参与"
                                                onToggled: root.updateRoleItem("variables", root.selectedVariableIndex, "stage_relevant", checked)
                                            }
                                        }

                                        SettingField {
                                            title: "最小值（min_value）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentVariable() ? root.numberValue(root.currentVariable().min_value, 0) : 0
                                                min: -1000000
                                                max: 1000000
                                                step: 1
                                                precision: 2
                                                onValueModified: root.updateRoleItem("variables", root.selectedVariableIndex, "min_value", value)
                                            }
                                        }

                                        SettingField {
                                            title: "最大值（max_value）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentVariable() ? root.numberValue(root.currentVariable().max_value, 100) : 100
                                                min: -1000000
                                                max: 1000000
                                                step: 1
                                                precision: 2
                                                onValueModified: root.updateRoleItem("variables", root.selectedVariableIndex, "max_value", value)
                                            }
                                        }

                                        SettingField {
                                            title: "单轮最小变化（delta_min）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentVariable() ? root.numberValue(root.currentVariable().delta_min, -5) : -5
                                                min: -1000000
                                                max: 1000000
                                                step: 1
                                                precision: 2
                                                onValueModified: root.updateRoleItem("variables", root.selectedVariableIndex, "delta_min", value)
                                            }
                                        }

                                        SettingField {
                                            title: "单轮最大变化（delta_max）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentVariable() ? root.numberValue(root.currentVariable().delta_max, 5) : 5
                                                min: -1000000
                                                max: 1000000
                                                step: 1
                                                precision: 2
                                                onValueModified: root.updateRoleItem("variables", root.selectedVariableIndex, "delta_max", value)
                                            }
                                        }
                                    }

                                    SettingField {
                                        Layout.fillWidth: true
                                        title: "变量判断说明（instruction）"

                                        HusTextArea {
                                            id: variableInstructionInput
                                            width: parent.width
                                            minRows: 3
                                            maxRows: 6
                                            maxLength: 4000
                                            autoSize: true
                                            resizable: true
                                            text: root.currentVariable() ? root.currentVariable().instruction : ""
                                            placeholderText: "说明变量在什么情况下变化，普通互动是否保持不变"
                                            onTextChanged: {
                                                if (activeFocus) {
                                                    root.updateRoleItem("variables", root.selectedVariableIndex, "instruction", text);
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                visible: root.databaseTab === "stages"

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    HusText {
                                        Layout.fillWidth: true
                                        text: "阶段规则"
                                        font.pixelSize: 17
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                    }

                                    HusButton {
                                        text: "新增"
                                        type: HusButton.Type_Primary
                                        onClicked: root.addStage()
                                    }

                                    HusButton {
                                        text: "删除"
                                        type: HusButton.Type_Outlined
                                        enabled: root.selectedStageIndex >= 0
                                        onClicked: root.removeStage()
                                    }
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 7

                                    Repeater {
                                        model: root.currentDatabaseRole() ? root.asArray(root.currentDatabaseRole().stages) : []

                                        delegate: HusButton {
                                            required property var modelData
                                            required property int index

                                            text: modelData.stage_name || modelData.stage_key || `阶段 ${index + 1}`
                                            type: index === root.selectedStageIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                            onClicked: root.selectedStageIndex = index
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 58
                                    radius: 6
                                    visible: root.currentDatabaseRole() && root.asArray(root.currentDatabaseRole().stages).length === 0
                                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.34)

                                    HusText {
                                        anchors.centerIn: parent
                                        text: "暂无阶段规则。阶段会根据变量条件激活。"
                                        color: HusTheme.Primary.colorTextSecondary
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 14
                                    visible: root.currentDatabaseRole() && root.selectedStageIndex >= 0 && root.selectedStageIndex < root.asArray(root.currentDatabaseRole().stages).length

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: root.narrowLayout ? 1 : 2
                                        columnSpacing: 14
                                        rowSpacing: 14

                                        SettingField {
                                            title: "启用（enabled）"

                                            HusSwitch {
                                                checked: root.currentStage() ? root.currentStage().enabled !== false : false
                                                checkedText: "开启"
                                                uncheckedText: "关闭"
                                                onToggled: root.updateRoleItem("stages", root.selectedStageIndex, "enabled", checked)
                                            }
                                        }

                                        SettingField {
                                            title: "允许回退（allow_regression）"

                                            HusSwitch {
                                                checked: root.currentStage() ? Boolean(root.currentStage().allow_regression) : false
                                                checkedText: "允许"
                                                uncheckedText: "禁止"
                                                onToggled: root.updateRoleItem("stages", root.selectedStageIndex, "allow_regression", checked)
                                            }
                                        }

                                        SettingField {
                                            title: "阶段键（stage_key）"

                                            HusInput {
                                                width: parent.width
                                                text: root.currentStage() ? root.currentStage().stage_key : ""
                                                placeholderText: "例如：stage_a"
                                                clearEnabled: "active"
                                                onTextEdited: root.updateRoleItem("stages", root.selectedStageIndex, "stage_key", text)
                                            }
                                        }

                                        SettingField {
                                            title: "阶段名称（stage_name）"

                                            HusInput {
                                                width: parent.width
                                                text: root.currentStage() ? root.currentStage().stage_name : ""
                                                placeholderText: "例如：A 阶段"
                                                clearEnabled: "active"
                                                onTextEdited: root.updateRoleItem("stages", root.selectedStageIndex, "stage_name", text)
                                            }
                                        }

                                        SettingField {
                                            title: "优先级（priority）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentStage() ? root.numberValue(root.currentStage().priority, 10) : 10
                                                min: -100000
                                                max: 100000
                                                step: 1
                                                precision: 0
                                                onValueModified: root.updateRoleItem("stages", root.selectedStageIndex, "priority", Math.round(value))
                                            }
                                        }

                                        SettingField {
                                            title: "条件关系（condition_mode）"

                                            HusSegmented {
                                                width: parent.width
                                                options: [
                                                    {
                                                        "label": "全部满足",
                                                        "value": "all"
                                                    },
                                                    {
                                                        "label": "任一满足",
                                                        "value": "any"
                                                    }
                                                ]
                                                currentIndex: root.currentStage() && root.currentStage().condition_mode === "any" ? 1 : 0
                                                onCurrentIndexChanged: root.updateRoleItem("stages", root.selectedStageIndex, "condition_mode", currentIndex === 1 ? "any" : "all")
                                            }
                                        }

                                        SettingField {
                                            title: "连续确认轮数（confirm_turns）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentStage() ? root.numberValue(root.currentStage().confirm_turns, 1) : 1
                                                min: 1
                                                max: 999
                                                step: 1
                                                precision: 0
                                                onValueModified: root.updateRoleItem("stages", root.selectedStageIndex, "confirm_turns", Math.round(value))
                                            }
                                        }

                                        SettingField {
                                            title: "冷却轮数（cooldown_turns）"

                                            HusInputNumber {
                                                width: parent.width
                                                value: root.currentStage() ? root.numberValue(root.currentStage().cooldown_turns, 0) : 0
                                                min: 0
                                                max: 999
                                                step: 1
                                                precision: 0
                                                onValueModified: root.updateRoleItem("stages", root.selectedStageIndex, "cooldown_turns", Math.round(value))
                                            }
                                        }
                                    }

                                    SettingField {
                                        Layout.fillWidth: true
                                        title: "阶段标签"
                                        description: "阶段命中后使用的 external_tag。保存时会根据 role_id 和 stage_key 重新生成。"

                                        HusInput {
                                            width: parent.width
                                            readOnly: true
                                            text: root.currentDatabaseRole() && root.currentStage() ? `database.stage.${root.currentDatabaseRole().role_id}.${root.currentStage().stage_key}` : ""
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        HusText {
                                            Layout.fillWidth: true
                                            text: "条件（conditions）"
                                            font.pixelSize: 16
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                        }

                                        HusButton {
                                            text: "新增条件"
                                            type: HusButton.Type_Filled
                                            onClicked: root.addStageCondition()
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        Repeater {
                                            model: root.currentStage() ? root.asArray(root.currentStage().conditions) : []

                                            delegate: Rectangle {
                                                required property var modelData
                                                required property int index

                                                Layout.fillWidth: true
                                                implicitHeight: conditionRow.implicitHeight + 18
                                                radius: 5
                                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.10 : 0.28)
                                                border.width: 1
                                                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                                                GridLayout {
                                                    id: conditionRow
                                                    anchors.fill: parent
                                                    anchors.margins: 9
                                                    columns: root.narrowLayout ? 1 : 4
                                                    columnSpacing: 8
                                                    rowSpacing: 8

                                                    HusInput {
                                                        Layout.fillWidth: true
                                                        placeholderText: "变量键（var）"
                                                        text: modelData.var || ""
                                                        onTextEdited: root.updateStageCondition(index, "var", text)
                                                    }

                                                    HusSegmented {
                                                        Layout.fillWidth: true
                                                        options: [
                                                            {
                                                                "label": ">",
                                                                "value": ">"
                                                            },
                                                            {
                                                                "label": ">=",
                                                                "value": ">="
                                                            },
                                                            {
                                                                "label": "<",
                                                                "value": "<"
                                                            },
                                                            {
                                                                "label": "<=",
                                                                "value": "<="
                                                            },
                                                            {
                                                                "label": "=",
                                                                "value": "="
                                                            },
                                                            {
                                                                "label": "!=",
                                                                "value": "!="
                                                            }
                                                        ]
                                                        currentIndex: Math.max(0, [">", ">=", "<", "<=", "=", "!="].indexOf(modelData.op || ">="))
                                                        onCurrentIndexChanged: root.updateStageCondition(index, "op", [">", ">=", "<", "<=", "=", "!="][currentIndex])
                                                    }

                                                    HusInputNumber {
                                                        Layout.fillWidth: true
                                                        value: root.numberValue(modelData.value, 0)
                                                        min: -1000000
                                                        max: 1000000
                                                        step: 1
                                                        precision: 2
                                                        onValueModified: root.updateStageCondition(index, "value", value)
                                                    }

                                                    HusButton {
                                                        text: "删除"
                                                        type: HusButton.Type_Outlined
                                                        onClicked: root.removeStageCondition(index)
                                                    }
                                                }
                                            }
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            visible: root.currentStage() && root.asArray(root.currentStage().conditions).length === 0
                                            text: "暂无条件。无条件阶段不会根据变量自动命中。"
                                            color: HusTheme.Primary.colorTextSecondary
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                visible: root.databaseTab === "snapshot"

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    HusText {
                                        Layout.fillWidth: true
                                        text: "状态快照字段"
                                        font.pixelSize: 17
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                    }

                                    HusButton {
                                        text: "新增"
                                        type: HusButton.Type_Primary
                                        onClicked: root.addSnapshotField()
                                    }

                                    HusButton {
                                        text: "删除"
                                        type: HusButton.Type_Outlined
                                        enabled: root.selectedSnapshotIndex >= 0
                                        onClicked: root.removeSnapshotField()
                                    }
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 7

                                    Repeater {
                                        model: root.currentDatabaseRole() ? root.asArray(root.currentDatabaseRole().snapshotFields) : []

                                        delegate: HusButton {
                                            required property var modelData
                                            required property int index

                                            text: modelData.label || modelData.key || `快照 ${index + 1}`
                                            type: index === root.selectedSnapshotIndex ? HusButton.Type_Primary : HusButton.Type_Outlined
                                            onClicked: root.selectedSnapshotIndex = index
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 58
                                    radius: 6
                                    visible: root.currentDatabaseRole() && root.asArray(root.currentDatabaseRole().snapshotFields).length === 0
                                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.34)

                                    HusText {
                                        anchors.centerIn: parent
                                        text: "暂无快照字段。未配置时会回落到全局默认状态记录模板。"
                                        color: HusTheme.Primary.colorTextSecondary
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 14
                                    visible: root.currentDatabaseRole() && root.selectedSnapshotIndex >= 0 && root.selectedSnapshotIndex < root.asArray(root.currentDatabaseRole().snapshotFields).length

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: root.narrowLayout ? 1 : 2
                                        columnSpacing: 14
                                        rowSpacing: 14

                                        SettingField {
                                            title: "启用（enabled）"

                                            HusSwitch {
                                                checked: root.currentSnapshotField() ? root.currentSnapshotField().enabled !== false : false
                                                checkedText: "开启"
                                                uncheckedText: "关闭"
                                                onToggled: root.updateRoleItem("snapshotFields", root.selectedSnapshotIndex, "enabled", checked)
                                            }
                                        }

                                        SettingField {
                                            title: "显示（display）"

                                            HusSwitch {
                                                checked: root.currentSnapshotField() ? root.currentSnapshotField().display !== false : false
                                                checkedText: "显示"
                                                uncheckedText: "隐藏"
                                                onToggled: root.updateRoleItem("snapshotFields", root.selectedSnapshotIndex, "display", checked)
                                            }
                                        }

                                        SettingField {
                                            title: "字段键（key）"

                                            HusInput {
                                                width: parent.width
                                                text: root.currentSnapshotField() ? root.currentSnapshotField().key : ""
                                                placeholderText: "例如：mood"
                                                clearEnabled: "active"
                                                onTextEdited: root.updateRoleItem("snapshotFields", root.selectedSnapshotIndex, "key", text)
                                            }
                                        }

                                        SettingField {
                                            title: "显示名称（label）"

                                            HusInput {
                                                width: parent.width
                                                text: root.currentSnapshotField() ? root.currentSnapshotField().label : ""
                                                placeholderText: "例如：当前情绪"
                                                clearEnabled: "active"
                                                onTextEdited: root.updateRoleItem("snapshotFields", root.selectedSnapshotIndex, "label", text)
                                            }
                                        }
                                    }

                                    SettingField {
                                        Layout.fillWidth: true
                                        title: "生成说明（instruction）"

                                        HusTextArea {
                                            id: snapshotInstructionInput
                                            width: parent.width
                                            minRows: 3
                                            maxRows: 6
                                            maxLength: 4000
                                            autoSize: true
                                            resizable: true
                                            text: root.currentSnapshotField() ? root.currentSnapshotField().instruction : ""
                                            placeholderText: "说明如何根据本轮上下文生成该状态快照字段"
                                            onTextChanged: {
                                                if (activeFocus) {
                                                    root.updateRoleItem("snapshotFields", root.selectedSnapshotIndex, "instruction", text);
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        ScrollBar.vertical: HusScrollBar {}
    }

    SmoothWheelArea {
        anchors.fill: scroller
        target: scroller
        childTargets: [personaList, databaseRoleList, descriptionInput, personalityInput, scenarioInput, firstMessageInput, messageExampleInput, creatorNotesInput, creatorCommentInput, personaDescriptionInput, personaPersonalityInput, personaScenarioInput, personaCreatorNotesInput, variableInstructionInput, snapshotInstructionInput]
    }
}
