"use strict";

const DEFAULT_FIND_RETRY_ATTEMPTS = 5;
const DEFAULT_FIND_RETRY_DELAY_MS = 2000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * @param {{
 *   github: import("@octokit/core").Octokit["graphql"] extends never ? any : { graphql: Function },
 *   projectOwner: string,
 *   projectNumber: number,
 *   dryRun?: boolean,
 *   findRetryAttempts?: number,
 *   findRetryDelayMs?: number,
 * }} options
 */
function createProjectV2Client(options) {
  const {
    github,
    projectOwner,
    projectNumber,
    dryRun = false,
    findRetryAttempts = DEFAULT_FIND_RETRY_ATTEMPTS,
    findRetryDelayMs = DEFAULT_FIND_RETRY_DELAY_MS,
  } = options;

  const projectFieldsSelection = `
    id
    fields(first: 100) {
      nodes {
        ... on ProjectV2SingleSelectField {
          id
          name
          options { id name }
        }
        ... on ProjectV2Field {
          id
          name
          dataType
        }
      }
    }`;

  async function loadProjectFromUser() {
    const query = `
      query($owner: String!, $number: Int!) {
        user(login: $owner) {
          projectV2(number: $number) {
            ${projectFieldsSelection}
          }
        }
      }`;
    const data = await github.graphql(query, { owner: projectOwner, number: projectNumber });
    return data.user?.projectV2 || null;
  }

  async function loadProjectFromOrganization() {
    const query = `
      query($owner: String!, $number: Int!) {
        organization(login: $owner) {
          projectV2(number: $number) {
            ${projectFieldsSelection}
          }
        }
      }`;
    try {
      const data = await github.graphql(query, { owner: projectOwner, number: projectNumber });
      return data.organization?.projectV2 || null;
    } catch (error) {
      const message = String(error.message || error);
      if (message.includes("Could not resolve to an Organization")) return null;
      throw error;
    }
  }

  async function loadProject() {
    if (!projectNumber) return null;
    const fromUser = await loadProjectFromUser();
    if (fromUser) return fromUser;
    return loadProjectFromOrganization();
  }

  async function getRepositoryIssueNodeId(owner, repo, issueNumber) {
    const query = `
      query($owner: String!, $repo: String!, $number: Int!) {
        repository(owner: $owner, name: $repo) {
          issue(number: $number) { id }
        }
      }`;
    const data = await github.graphql(query, { owner, repo, number: issueNumber });
    return data.repository?.issue?.id || null;
  }

  async function findProjectItemOnce(project, issueNodeId) {
    const query = `
      query($projectId: ID!, $after: String) {
        node(id: $projectId) {
          ... on ProjectV2 {
            items(first: 100, after: $after) {
              nodes {
                id
                content { ... on Issue { id } }
              }
              pageInfo { hasNextPage endCursor }
            }
          }
        }
      }`;
    let after = null;
    for (;;) {
      const data = await github.graphql(query, { projectId: project.id, after });
      const items = data.node?.items;
      const hit = items?.nodes?.find((item) => item.content?.id === issueNodeId);
      if (hit) return hit.id;
      if (!items?.pageInfo?.hasNextPage) return null;
      after = items.pageInfo.endCursor;
    }
  }

  /**
   * @param {object} project
   * @param {string} issueNodeId
   * @param {{ retry?: boolean }} [opts]
   */
  async function findProjectItem(project, issueNodeId, opts = {}) {
    const attempts = opts.retry === false ? 1 : findRetryAttempts;
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      const itemId = await findProjectItemOnce(project, issueNodeId);
      if (itemId) return itemId;
      if (attempt < attempts) await sleep(findRetryDelayMs);
    }
    return null;
  }

  /**
   * @param {object} project
   * @param {string} issueNodeId
   * @param {{ retryFind?: boolean }} [opts]
   */
  async function ensureProjectItem(project, issueNodeId, opts = {}) {
    const retryFind = opts.retryFind !== false;
    if (dryRun) {
      const existingItemId = await findProjectItem(project, issueNodeId, { retry: false });
      if (existingItemId) return existingItemId;
      return "dry-run-project-item";
    }

    const mutation = `
      mutation($projectId: ID!, $contentId: ID!) {
        addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
          item { id }
        }
      }`;
    try {
      const data = await github.graphql(mutation, { projectId: project.id, contentId: issueNodeId });
      const itemId = data.addProjectV2ItemById?.item?.id;
      if (itemId) return itemId;
    } catch (error) {
      const message = String(error.message || error);
      if (!message.includes("already exists")) throw error;
    }

    return findProjectItem(project, issueNodeId, { retry: retryFind });
  }

  async function getFieldDateValue(itemId, fieldName) {
    const query = `
      query($itemId: ID!, $fieldName: String!) {
        node(id: $itemId) {
          ... on ProjectV2Item {
            fieldValueByName(name: $fieldName) {
              ... on ProjectV2ItemFieldDateValue { date }
            }
          }
        }
      }`;
    const data = await github.graphql(query, { itemId, fieldName });
    return data.node?.fieldValueByName?.date || "";
  }

  async function readItemStatus(itemId) {
    const query = `
      query($itemId: ID!) {
        node(id: $itemId) {
          ... on ProjectV2Item {
            fieldValueByName(name: "Status") {
              ... on ProjectV2ItemFieldSingleSelectValue { name }
            }
          }
        }
      }`;
    const data = await github.graphql(query, { itemId });
    return data.node?.fieldValueByName?.name || "";
  }

  async function readIssueStatus(owner, repo, issueNumber) {
    try {
      const project = await loadProject();
      if (!project) return "";
      const issueNodeId = await getRepositoryIssueNodeId(owner, repo, issueNumber);
      if (!issueNodeId) return "";
      const itemId = await findProjectItem(project, issueNodeId, { retry: false });
      if (!itemId) return "";
      return readItemStatus(itemId);
    } catch {
      return "";
    }
  }

  function fieldByName(project, name) {
    return project.fields.nodes.find((field) => field.name === name);
  }

  function optionFor(field, values) {
    if (!field?.options) return null;
    const candidates = values.filter(Boolean).map(String);
    return field.options.find((option) => candidates.includes(option.name));
  }

  async function updateSingleSelect(project, itemId, fieldName, values) {
    const field = fieldByName(project, fieldName);
    const option = optionFor(field, values);
    if (!field || !option) return false;
    const mutation = `
      mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
        updateProjectV2ItemFieldValue(input: {
          projectId: $projectId,
          itemId: $itemId,
          fieldId: $fieldId,
          value: { singleSelectOptionId: $optionId }
        }) { projectV2Item { id } }
      }`;
    if (!dryRun) {
      await github.graphql(mutation, {
        projectId: project.id,
        itemId,
        fieldId: field.id,
        optionId: option.id,
      });
    }
    return true;
  }

  async function updateDate(project, itemId, fieldName, value) {
    const field = fieldByName(project, fieldName);
    const date = String(value || "")
      .trim()
      .split(/\r?\n/)[0]
      .trim();
    if (!field || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
    const mutation = `
      mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $date: Date!) {
        updateProjectV2ItemFieldValue(input: {
          projectId: $projectId,
          itemId: $itemId,
          fieldId: $fieldId,
          value: { date: $date }
        }) { projectV2Item { id } }
      }`;
    if (!dryRun) {
      await github.graphql(mutation, {
        projectId: project.id,
        itemId,
        fieldId: field.id,
        date,
      });
    }
    return true;
  }

  async function updateStatus(project, itemId, statusName) {
    const updated = await updateSingleSelect(project, itemId, "Status", [statusName]);
    if (!updated) throw new Error(`Project Status option not found: ${statusName}`);
  }

  return {
    loadProject,
    getRepositoryIssueNodeId,
    findProjectItem,
    ensureProjectItem,
    getFieldDateValue,
    readItemStatus,
    readIssueStatus,
    fieldByName,
    optionFor,
    updateSingleSelect,
    updateDate,
    updateStatus,
    sleep,
  };
}

module.exports = {
  createProjectV2Client,
  sleep,
  DEFAULT_FIND_RETRY_ATTEMPTS,
  DEFAULT_FIND_RETRY_DELAY_MS,
};
