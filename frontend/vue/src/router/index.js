import { createRouter, createWebHistory } from "vue-router";

import ApplicationDetailPage from "../pages/ApplicationDetailPage.vue";
import AnalyticsPage from "../pages/AnalyticsPage.vue";
import ApplicationsPage from "../pages/ApplicationsPage.vue";
import ApplyPage from "../pages/ApplyPage.vue";
import CompanyDetailPage from "../pages/CompanyDetailPage.vue";
import CompaniesPage from "../pages/CompaniesPage.vue";
import DashboardPage from "../pages/DashboardPage.vue";
import DraftDetailPage from "../pages/DraftDetailPage.vue";
import DraftsPage from "../pages/DraftsPage.vue";
import HelpPage from "../pages/HelpPage.vue";
import JobDetailPage from "../pages/JobDetailPage.vue";
import JobsPage from "../pages/JobsPage.vue";
import OfferCompassPage from "../pages/OfferCompassPage.vue";
import OnboardingPage from "../pages/OnboardingPage.vue";
import AiProviderSettingsPage from "../pages/settings/AiProviderSettingsPage.vue";
import WorkspaceSettingsPage from "../pages/settings/WorkspaceSettingsPage.vue";
import SetupRequiredPage from "../pages/SetupRequiredPage.vue";
import StoryBankPage from "../pages/StoryBankPage.vue";
import ThesisPage from "../pages/ThesisPage.vue";
import VerifiedFactsPage from "../pages/VerifiedFactsPage.vue";
import WelcomePage from "../pages/WelcomePage.vue";
import WorkspaceResetPage from "../pages/WorkspaceResetPage.vue";
import NotFoundPage from "../pages/NotFoundPage.vue";

const routes = [
  {
    path: "/",
    name: "welcome",
    component: WelcomePage,
    meta: { layout: "blank" }
  },
  {
    path: "/dashboard",
    name: "dashboard",
    component: DashboardPage
  },
  {
    path: "/jobs",
    name: "jobs",
    component: JobsPage
  },
  {
    path: "/jobs/:id",
    name: "job-detail",
    component: JobDetailPage
  },
  {
    path: "/companies",
    name: "companies",
    component: CompaniesPage
  },
  {
    path: "/companies/:id",
    name: "company-detail",
    component: CompanyDetailPage
  },
  {
    path: "/apply",
    name: "apply",
    component: ApplyPage
  },
  {
    path: "/applications",
    name: "applications",
    component: ApplicationsPage
  },
  {
    path: "/applications/:id",
    name: "application-detail",
    component: ApplicationDetailPage
  },
  {
    path: "/drafts",
    name: "drafts",
    component: DraftsPage
  },
  {
    path: "/drafts/:id",
    name: "draft-detail",
    component: DraftDetailPage
  },
  {
    path: "/onboarding",
    name: "onboarding",
    component: OnboardingPage,
    meta: { layout: "blank" }
  },
  {
    path: "/settings",
    redirect: "/settings/ai-provider"
  },
  {
    path: "/settings/ai-provider",
    name: "settings-ai-provider",
    component: AiProviderSettingsPage
  },
  {
    path: "/settings/workspace",
    name: "settings-workspace",
    component: WorkspaceSettingsPage
  },
  {
    path: "/setup-required",
    name: "setup-required",
    component: SetupRequiredPage
  },
  {
    path: "/verified-facts",
    name: "verified-facts",
    component: VerifiedFactsPage
  },
  {
    path: "/story-bank",
    name: "story-bank",
    component: StoryBankPage
  },
  {
    path: "/offer-compass",
    name: "offer-compass",
    component: OfferCompassPage
  },
  {
    path: "/analytics",
    name: "analytics",
    component: AnalyticsPage
  },
  {
    path: "/thesis",
    name: "thesis",
    component: ThesisPage
  },
  {
    path: "/workspace-reset",
    name: "workspace-reset",
    component: WorkspaceResetPage
  },
  {
    path: "/help",
    name: "help",
    component: HelpPage
  },
  {
    path: "/about",
    redirect: "/"
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: NotFoundPage
  }
];

const router = createRouter({
  history: createWebHistory("/app"),
  routes
});

export default router;
