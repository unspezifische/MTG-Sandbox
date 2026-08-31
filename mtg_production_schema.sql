--
-- PostgreSQL database dump
--

\restrict NeU155LuQOEyKNQlQXlHepProYhUjwUe8CcGTGSgtzRN7UV1uak65anqJ49fxqq

-- Dumped from database version 17.9 (Debian 17.9-0+deb13u1)
-- Dumped by pg_dump version 17.9 (Debian 17.9-0+deb13u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: mtgAnalysis; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA "mtgAnalysis";


--
-- Name: mtgCore; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA "mtgCore";


--
-- Name: mtgDecks; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA "mtgDecks";


--
-- Name: mtgGames; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA "mtgGames";


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: archetypes; Type: TABLE; Schema: mtgAnalysis; Owner: -
--

CREATE TABLE "mtgAnalysis".archetypes (
    id bigint NOT NULL,
    name text NOT NULL,
    description text,
    "tagsJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: archetypes_id_seq; Type: SEQUENCE; Schema: mtgAnalysis; Owner: -
--

CREATE SEQUENCE "mtgAnalysis".archetypes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: archetypes_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgAnalysis; Owner: -
--

ALTER SEQUENCE "mtgAnalysis".archetypes_id_seq OWNED BY "mtgAnalysis".archetypes.id;


--
-- Name: cardMatchupTags; Type: TABLE; Schema: mtgAnalysis; Owner: -
--

CREATE TABLE "mtgAnalysis"."cardMatchupTags" (
    id bigint NOT NULL,
    "cardId" bigint NOT NULL,
    "relationType" text NOT NULL,
    "targetTag" text NOT NULL,
    weight numeric,
    source text,
    confidence numeric,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: cardMatchupTags_id_seq; Type: SEQUENCE; Schema: mtgAnalysis; Owner: -
--

CREATE SEQUENCE "mtgAnalysis"."cardMatchupTags_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cardMatchupTags_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgAnalysis; Owner: -
--

ALTER SEQUENCE "mtgAnalysis"."cardMatchupTags_id_seq" OWNED BY "mtgAnalysis"."cardMatchupTags".id;


--
-- Name: cardRoleTags; Type: TABLE; Schema: mtgAnalysis; Owner: -
--

CREATE TABLE "mtgAnalysis"."cardRoleTags" (
    id bigint NOT NULL,
    "cardId" bigint NOT NULL,
    "roleType" text NOT NULL,
    "roleValue" text NOT NULL,
    weight numeric,
    source text,
    confidence numeric,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: cardRoleTags_id_seq; Type: SEQUENCE; Schema: mtgAnalysis; Owner: -
--

CREATE SEQUENCE "mtgAnalysis"."cardRoleTags_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cardRoleTags_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgAnalysis; Owner: -
--

ALTER SEQUENCE "mtgAnalysis"."cardRoleTags_id_seq" OWNED BY "mtgAnalysis"."cardRoleTags".id;


--
-- Name: deckMatchupProfiles; Type: TABLE; Schema: mtgAnalysis; Owner: -
--

CREATE TABLE "mtgAnalysis"."deckMatchupProfiles" (
    id bigint NOT NULL,
    "deckSnapshotId" bigint NOT NULL,
    "archetypeName" text NOT NULL,
    "strengthScore" numeric,
    confidence numeric,
    notes text,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: deckMatchupProfiles_id_seq; Type: SEQUENCE; Schema: mtgAnalysis; Owner: -
--

CREATE SEQUENCE "mtgAnalysis"."deckMatchupProfiles_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckMatchupProfiles_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgAnalysis; Owner: -
--

ALTER SEQUENCE "mtgAnalysis"."deckMatchupProfiles_id_seq" OWNED BY "mtgAnalysis"."deckMatchupProfiles".id;


--
-- Name: deckMetrics; Type: TABLE; Schema: mtgAnalysis; Owner: -
--

CREATE TABLE "mtgAnalysis"."deckMetrics" (
    id bigint NOT NULL,
    "deckSnapshotId" bigint NOT NULL,
    "metricGroup" text,
    "metricName" text NOT NULL,
    "metricValueNumeric" numeric,
    "metricValueText" text,
    "metricValueJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: deckMetrics_id_seq; Type: SEQUENCE; Schema: mtgAnalysis; Owner: -
--

CREATE SEQUENCE "mtgAnalysis"."deckMetrics_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckMetrics_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgAnalysis; Owner: -
--

ALTER SEQUENCE "mtgAnalysis"."deckMetrics_id_seq" OWNED BY "mtgAnalysis"."deckMetrics".id;


--
-- Name: deckSnapshots; Type: TABLE; Schema: mtgAnalysis; Owner: -
--

CREATE TABLE "mtgAnalysis"."deckSnapshots" (
    id bigint NOT NULL,
    "deckId" bigint NOT NULL,
    "deckVersionId" bigint,
    "summaryJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: deckSnapshots_id_seq; Type: SEQUENCE; Schema: mtgAnalysis; Owner: -
--

CREATE SEQUENCE "mtgAnalysis"."deckSnapshots_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckSnapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgAnalysis; Owner: -
--

ALTER SEQUENCE "mtgAnalysis"."deckSnapshots_id_seq" OWNED BY "mtgAnalysis"."deckSnapshots".id;


--
-- Name: simulationRuns; Type: TABLE; Schema: mtgAnalysis; Owner: -
--

CREATE TABLE "mtgAnalysis"."simulationRuns" (
    id bigint NOT NULL,
    "deckId" bigint NOT NULL,
    "deckVersionId" bigint,
    "runType" text NOT NULL,
    "opponentProfile" text,
    "simulationCount" integer NOT NULL,
    "configJson" jsonb,
    "resultSummaryJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: simulationRuns_id_seq; Type: SEQUENCE; Schema: mtgAnalysis; Owner: -
--

CREATE SEQUENCE "mtgAnalysis"."simulationRuns_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: simulationRuns_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgAnalysis; Owner: -
--

ALTER SEQUENCE "mtgAnalysis"."simulationRuns_id_seq" OWNED BY "mtgAnalysis"."simulationRuns".id;


--
-- Name: cardFaces; Type: TABLE; Schema: mtgCore; Owner: -
--

CREATE TABLE "mtgCore"."cardFaces" (
    id bigint NOT NULL,
    "cardId" bigint NOT NULL,
    "faceOrder" integer NOT NULL,
    name text NOT NULL,
    "manaCost" text,
    "typeLine" text,
    "oracleText" text,
    power text,
    toughness text,
    loyalty text,
    defense text,
    colors text[],
    identifiers jsonb,
    "rawJson" jsonb
);


--
-- Name: cardFaces_id_seq; Type: SEQUENCE; Schema: mtgCore; Owner: -
--

CREATE SEQUENCE "mtgCore"."cardFaces_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cardFaces_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgCore; Owner: -
--

ALTER SEQUENCE "mtgCore"."cardFaces_id_seq" OWNED BY "mtgCore"."cardFaces".id;


--
-- Name: cards; Type: TABLE; Schema: mtgCore; Owner: -
--

CREATE TABLE "mtgCore".cards (
    id bigint NOT NULL,
    uuid text NOT NULL,
    "oracleId" text,
    name text NOT NULL,
    "normalizedName" text,
    "faceName" text,
    "manaCost" text,
    "manaValue" numeric,
    colors text[],
    "colorIdentity" text[],
    "typeLine" text,
    "oracleText" text,
    power text,
    toughness text,
    loyalty text,
    defense text,
    layout text,
    side text,
    "isToken" boolean,
    "isReserved" boolean,
    "isReprint" boolean,
    "edhrecRank" integer,
    "defaultSetCode" text,
    "defaultSetName" text,
    rarity text,
    availability text[],
    identifiers jsonb,
    legalities jsonb,
    "rawJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL,
    "updatedAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: cards_id_seq; Type: SEQUENCE; Schema: mtgCore; Owner: -
--

CREATE SEQUENCE "mtgCore".cards_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cards_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgCore; Owner: -
--

ALTER SEQUENCE "mtgCore".cards_id_seq OWNED BY "mtgCore".cards.id;


--
-- Name: printingImages; Type: TABLE; Schema: mtgCore; Owner: -
--

CREATE TABLE "mtgCore"."printingImages" (
    id bigint NOT NULL,
    "printingId" bigint NOT NULL,
    "faceName" text NOT NULL,
    "imageSize" text NOT NULL,
    "localPath" text,
    "publicUrl" text,
    "sourceUrl" text,
    status text NOT NULL,
    "contentType" text,
    "fileBytes" bigint,
    "lastError" text,
    "lastAttemptedAt" timestamp with time zone,
    "downloadedAt" timestamp with time zone,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL,
    "updatedAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: printingImages_id_seq; Type: SEQUENCE; Schema: mtgCore; Owner: -
--

CREATE SEQUENCE "mtgCore"."printingImages_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: printingImages_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgCore; Owner: -
--

ALTER SEQUENCE "mtgCore"."printingImages_id_seq" OWNED BY "mtgCore"."printingImages".id;


--
-- Name: printings; Type: TABLE; Schema: mtgCore; Owner: -
--

CREATE TABLE "mtgCore".printings (
    id bigint NOT NULL,
    "cardId" bigint NOT NULL,
    "setId" bigint,
    uuid text NOT NULL,
    "collectorNumber" text,
    rarity text,
    artist text,
    "flavorText" text,
    "frameVersion" text,
    "borderColor" text,
    language text,
    "isPromo" boolean,
    "isFullArt" boolean,
    availability text[],
    identifiers jsonb,
    "rawJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: printings_id_seq; Type: SEQUENCE; Schema: mtgCore; Owner: -
--

CREATE SEQUENCE "mtgCore".printings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: printings_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgCore; Owner: -
--

ALTER SEQUENCE "mtgCore".printings_id_seq OWNED BY "mtgCore".printings.id;


--
-- Name: productContents; Type: TABLE; Schema: mtgCore; Owner: -
--

CREATE TABLE "mtgCore"."productContents" (
    id bigint NOT NULL,
    "productId" bigint NOT NULL,
    "cardId" bigint NOT NULL,
    quantity integer NOT NULL,
    "isCommander" boolean,
    "boardSection" text,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: productContents_id_seq; Type: SEQUENCE; Schema: mtgCore; Owner: -
--

CREATE SEQUENCE "mtgCore"."productContents_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: productContents_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgCore; Owner: -
--

ALTER SEQUENCE "mtgCore"."productContents_id_seq" OWNED BY "mtgCore"."productContents".id;


--
-- Name: products; Type: TABLE; Schema: mtgCore; Owner: -
--

CREATE TABLE "mtgCore".products (
    id bigint NOT NULL,
    "productCode" text,
    name text NOT NULL,
    "productType" text,
    "setId" bigint,
    "releaseDate" date,
    "rawJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: products_id_seq; Type: SEQUENCE; Schema: mtgCore; Owner: -
--

CREATE SEQUENCE "mtgCore".products_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgCore; Owner: -
--

ALTER SEQUENCE "mtgCore".products_id_seq OWNED BY "mtgCore".products.id;


--
-- Name: sets; Type: TABLE; Schema: mtgCore; Owner: -
--

CREATE TABLE "mtgCore".sets (
    id bigint NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    "releaseDate" date,
    block text,
    "setType" text,
    "isDigital" boolean,
    "totalCards" integer,
    "tokenCount" integer,
    "rawJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sets_id_seq; Type: SEQUENCE; Schema: mtgCore; Owner: -
--

CREATE SEQUENCE "mtgCore".sets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sets_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgCore; Owner: -
--

ALTER SEQUENCE "mtgCore".sets_id_seq OWNED BY "mtgCore".sets.id;


--
-- Name: deckCards; Type: TABLE; Schema: mtgDecks; Owner: -
--

CREATE TABLE "mtgDecks"."deckCards" (
    id bigint NOT NULL,
    "deckId" bigint NOT NULL,
    "cardId" bigint NOT NULL,
    "preferredPrintingId" bigint,
    quantity integer NOT NULL,
    "boardType" text NOT NULL,
    "isCommander" boolean,
    "addedAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: deckCards_id_seq; Type: SEQUENCE; Schema: mtgDecks; Owner: -
--

CREATE SEQUENCE "mtgDecks"."deckCards_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckCards_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgDecks; Owner: -
--

ALTER SEQUENCE "mtgDecks"."deckCards_id_seq" OWNED BY "mtgDecks"."deckCards".id;


--
-- Name: deckImports; Type: TABLE; Schema: mtgDecks; Owner: -
--

CREATE TABLE "mtgDecks"."deckImports" (
    id bigint NOT NULL,
    "deckId" bigint NOT NULL,
    "importSource" text,
    "originalPayload" jsonb,
    "importedAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: deckImports_id_seq; Type: SEQUENCE; Schema: mtgDecks; Owner: -
--

CREATE SEQUENCE "mtgDecks"."deckImports_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckImports_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgDecks; Owner: -
--

ALTER SEQUENCE "mtgDecks"."deckImports_id_seq" OWNED BY "mtgDecks"."deckImports".id;


--
-- Name: deckTags; Type: TABLE; Schema: mtgDecks; Owner: -
--

CREATE TABLE "mtgDecks"."deckTags" (
    id bigint NOT NULL,
    "deckId" bigint NOT NULL,
    "tagType" text NOT NULL,
    "tagValue" text NOT NULL,
    source text,
    confidence numeric,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: deckTags_id_seq; Type: SEQUENCE; Schema: mtgDecks; Owner: -
--

CREATE SEQUENCE "mtgDecks"."deckTags_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckTags_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgDecks; Owner: -
--

ALTER SEQUENCE "mtgDecks"."deckTags_id_seq" OWNED BY "mtgDecks"."deckTags".id;


--
-- Name: deckVersionCards; Type: TABLE; Schema: mtgDecks; Owner: -
--

CREATE TABLE "mtgDecks"."deckVersionCards" (
    id bigint NOT NULL,
    "deckVersionId" bigint NOT NULL,
    "cardId" bigint NOT NULL,
    "preferredPrintingId" bigint,
    quantity integer NOT NULL,
    "boardType" text NOT NULL,
    "isCommander" boolean
);


--
-- Name: deckVersionCards_id_seq; Type: SEQUENCE; Schema: mtgDecks; Owner: -
--

CREATE SEQUENCE "mtgDecks"."deckVersionCards_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckVersionCards_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgDecks; Owner: -
--

ALTER SEQUENCE "mtgDecks"."deckVersionCards_id_seq" OWNED BY "mtgDecks"."deckVersionCards".id;


--
-- Name: deckVersions; Type: TABLE; Schema: mtgDecks; Owner: -
--

CREATE TABLE "mtgDecks"."deckVersions" (
    id bigint NOT NULL,
    "deckId" bigint NOT NULL,
    "versionNumber" integer NOT NULL,
    label text,
    "changeSummary" text,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: deckVersions_id_seq; Type: SEQUENCE; Schema: mtgDecks; Owner: -
--

CREATE SEQUENCE "mtgDecks"."deckVersions_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: deckVersions_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgDecks; Owner: -
--

ALTER SEQUENCE "mtgDecks"."deckVersions_id_seq" OWNED BY "mtgDecks"."deckVersions".id;


--
-- Name: decks; Type: TABLE; Schema: mtgDecks; Owner: -
--

CREATE TABLE "mtgDecks".decks (
    id bigint NOT NULL,
    name text NOT NULL,
    slug text,
    format text NOT NULL,
    "commanderCount" integer,
    "colorIdentity" text[],
    "ownerUserId" bigint,
    "sourceType" text,
    "sourceProductId" bigint,
    notes text,
    "isPublic" boolean,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL,
    "updatedAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: decks_id_seq; Type: SEQUENCE; Schema: mtgDecks; Owner: -
--

CREATE SEQUENCE "mtgDecks".decks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: decks_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgDecks; Owner: -
--

ALTER SEQUENCE "mtgDecks".decks_id_seq OWNED BY "mtgDecks".decks.id;


--
-- Name: branches; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames".branches (
    id bigint NOT NULL,
    "parentGameId" bigint NOT NULL,
    "childGameId" bigint NOT NULL,
    "parentSnapshotId" bigint,
    "branchLabel" text,
    "branchReason" text,
    "createdByUserId" bigint,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: branches_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames".branches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: branches_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames".branches_id_seq OWNED BY "mtgGames".branches.id;


--
-- Name: cardInstances; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames"."cardInstances" (
    id bigint NOT NULL,
    "gameId" bigint NOT NULL,
    "gamePlayerId" bigint,
    "cardId" bigint,
    "printingId" bigint,
    "sourceDeckCardId" bigint,
    "instanceType" text NOT NULL,
    "createdByEventId" bigint,
    "metadataJson" jsonb,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: cardInstances_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames"."cardInstances_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cardInstances_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames"."cardInstances_id_seq" OWNED BY "mtgGames"."cardInstances".id;


--
-- Name: decisions; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames".decisions (
    id bigint NOT NULL,
    "gameId" bigint NOT NULL,
    "gamePlayerId" bigint NOT NULL,
    "snapshotId" bigint,
    "sequenceNumber" bigint NOT NULL,
    "decisionType" text NOT NULL,
    "stateFeaturesJson" jsonb,
    "legalActionsJson" jsonb,
    "chosenActionJson" jsonb,
    "actionTakenEventId" bigint,
    "decisionSource" text NOT NULL,
    "timeTakenMs" integer,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: decisions_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames".decisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: decisions_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames".decisions_id_seq OWNED BY "mtgGames".decisions.id;


--
-- Name: events; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames".events (
    id bigint NOT NULL,
    "gameId" bigint NOT NULL,
    "sequenceNumber" bigint NOT NULL,
    "turnNumber" integer,
    phase text,
    step text,
    "actingGamePlayerId" bigint,
    "eventType" text NOT NULL,
    "visibilityScope" text,
    "payloadJson" jsonb NOT NULL,
    "publicText" text,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames".events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames".events_id_seq OWNED BY "mtgGames".events.id;


--
-- Name: gamePlayerLibraries; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames"."gamePlayerLibraries" (
    id bigint NOT NULL,
    "gamePlayerId" bigint NOT NULL,
    "zoneScope" text NOT NULL,
    "orderedCardInstanceIds" jsonb NOT NULL,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: gamePlayerLibraries_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames"."gamePlayerLibraries_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gamePlayerLibraries_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames"."gamePlayerLibraries_id_seq" OWNED BY "mtgGames"."gamePlayerLibraries".id;


--
-- Name: gamePlayers; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames"."gamePlayers" (
    id bigint NOT NULL,
    "gameId" bigint NOT NULL,
    "seatNumber" integer NOT NULL,
    "playerType" text NOT NULL,
    "userId" bigint,
    "aiProfile" text,
    "deckId" bigint,
    "deckVersionId" bigint,
    "startingLife" integer,
    "startingHandSize" integer,
    "finalPlacement" integer,
    result text,
    "commanderCastCount" integer,
    "commanderDamageDealt" integer,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: gamePlayers_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames"."gamePlayers_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: gamePlayers_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames"."gamePlayers_id_seq" OWNED BY "mtgGames"."gamePlayers".id;


--
-- Name: games; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames".games (
    id bigint NOT NULL,
    "parentGameId" bigint,
    "parentSnapshotId" bigint,
    "branchedFromSequence" bigint,
    "rootGameId" bigint,
    "gameMode" text NOT NULL,
    format text NOT NULL,
    status text NOT NULL,
    "rngSeed" text,
    "engineVersion" text,
    "rulesVersion" text,
    "startedAt" timestamp with time zone,
    "endedAt" timestamp with time zone,
    "winnerGamePlayerId" bigint,
    notes text,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: games_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames".games_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: games_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames".games_id_seq OWNED BY "mtgGames".games.id;


--
-- Name: stateSnapshots; Type: TABLE; Schema: mtgGames; Owner: -
--

CREATE TABLE "mtgGames"."stateSnapshots" (
    id bigint NOT NULL,
    "gameId" bigint NOT NULL,
    "sequenceNumber" bigint NOT NULL,
    "turnNumber" integer,
    phase text,
    "stateJson" jsonb NOT NULL,
    "snapshotHash" text,
    "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: stateSnapshots_id_seq; Type: SEQUENCE; Schema: mtgGames; Owner: -
--

CREATE SEQUENCE "mtgGames"."stateSnapshots_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stateSnapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: mtgGames; Owner: -
--

ALTER SEQUENCE "mtgGames"."stateSnapshots_id_seq" OWNED BY "mtgGames"."stateSnapshots".id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: archetypes id; Type: DEFAULT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis".archetypes ALTER COLUMN id SET DEFAULT nextval('"mtgAnalysis".archetypes_id_seq'::regclass);


--
-- Name: cardMatchupTags id; Type: DEFAULT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."cardMatchupTags" ALTER COLUMN id SET DEFAULT nextval('"mtgAnalysis"."cardMatchupTags_id_seq"'::regclass);


--
-- Name: cardRoleTags id; Type: DEFAULT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."cardRoleTags" ALTER COLUMN id SET DEFAULT nextval('"mtgAnalysis"."cardRoleTags_id_seq"'::regclass);


--
-- Name: deckMatchupProfiles id; Type: DEFAULT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckMatchupProfiles" ALTER COLUMN id SET DEFAULT nextval('"mtgAnalysis"."deckMatchupProfiles_id_seq"'::regclass);


--
-- Name: deckMetrics id; Type: DEFAULT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckMetrics" ALTER COLUMN id SET DEFAULT nextval('"mtgAnalysis"."deckMetrics_id_seq"'::regclass);


--
-- Name: deckSnapshots id; Type: DEFAULT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckSnapshots" ALTER COLUMN id SET DEFAULT nextval('"mtgAnalysis"."deckSnapshots_id_seq"'::regclass);


--
-- Name: simulationRuns id; Type: DEFAULT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."simulationRuns" ALTER COLUMN id SET DEFAULT nextval('"mtgAnalysis"."simulationRuns_id_seq"'::regclass);


--
-- Name: cardFaces id; Type: DEFAULT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."cardFaces" ALTER COLUMN id SET DEFAULT nextval('"mtgCore"."cardFaces_id_seq"'::regclass);


--
-- Name: cards id; Type: DEFAULT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".cards ALTER COLUMN id SET DEFAULT nextval('"mtgCore".cards_id_seq'::regclass);


--
-- Name: printingImages id; Type: DEFAULT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."printingImages" ALTER COLUMN id SET DEFAULT nextval('"mtgCore"."printingImages_id_seq"'::regclass);


--
-- Name: printings id; Type: DEFAULT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".printings ALTER COLUMN id SET DEFAULT nextval('"mtgCore".printings_id_seq'::regclass);


--
-- Name: productContents id; Type: DEFAULT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."productContents" ALTER COLUMN id SET DEFAULT nextval('"mtgCore"."productContents_id_seq"'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".products ALTER COLUMN id SET DEFAULT nextval('"mtgCore".products_id_seq'::regclass);


--
-- Name: sets id; Type: DEFAULT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".sets ALTER COLUMN id SET DEFAULT nextval('"mtgCore".sets_id_seq'::regclass);


--
-- Name: deckCards id; Type: DEFAULT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckCards" ALTER COLUMN id SET DEFAULT nextval('"mtgDecks"."deckCards_id_seq"'::regclass);


--
-- Name: deckImports id; Type: DEFAULT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckImports" ALTER COLUMN id SET DEFAULT nextval('"mtgDecks"."deckImports_id_seq"'::regclass);


--
-- Name: deckTags id; Type: DEFAULT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckTags" ALTER COLUMN id SET DEFAULT nextval('"mtgDecks"."deckTags_id_seq"'::regclass);


--
-- Name: deckVersionCards id; Type: DEFAULT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersionCards" ALTER COLUMN id SET DEFAULT nextval('"mtgDecks"."deckVersionCards_id_seq"'::regclass);


--
-- Name: deckVersions id; Type: DEFAULT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersions" ALTER COLUMN id SET DEFAULT nextval('"mtgDecks"."deckVersions_id_seq"'::regclass);


--
-- Name: decks id; Type: DEFAULT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks".decks ALTER COLUMN id SET DEFAULT nextval('"mtgDecks".decks_id_seq'::regclass);


--
-- Name: branches id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".branches ALTER COLUMN id SET DEFAULT nextval('"mtgGames".branches_id_seq'::regclass);


--
-- Name: cardInstances id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances" ALTER COLUMN id SET DEFAULT nextval('"mtgGames"."cardInstances_id_seq"'::regclass);


--
-- Name: decisions id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".decisions ALTER COLUMN id SET DEFAULT nextval('"mtgGames".decisions_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".events ALTER COLUMN id SET DEFAULT nextval('"mtgGames".events_id_seq'::regclass);


--
-- Name: gamePlayerLibraries id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayerLibraries" ALTER COLUMN id SET DEFAULT nextval('"mtgGames"."gamePlayerLibraries_id_seq"'::regclass);


--
-- Name: gamePlayers id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayers" ALTER COLUMN id SET DEFAULT nextval('"mtgGames"."gamePlayers_id_seq"'::regclass);


--
-- Name: games id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".games ALTER COLUMN id SET DEFAULT nextval('"mtgGames".games_id_seq'::regclass);


--
-- Name: stateSnapshots id; Type: DEFAULT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."stateSnapshots" ALTER COLUMN id SET DEFAULT nextval('"mtgGames"."stateSnapshots_id_seq"'::regclass);


--
-- Name: archetypes archetypes_pkey; Type: CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis".archetypes
    ADD CONSTRAINT archetypes_pkey PRIMARY KEY (id);


--
-- Name: cardMatchupTags cardMatchupTags_pkey; Type: CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."cardMatchupTags"
    ADD CONSTRAINT "cardMatchupTags_pkey" PRIMARY KEY (id);


--
-- Name: cardRoleTags cardRoleTags_pkey; Type: CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."cardRoleTags"
    ADD CONSTRAINT "cardRoleTags_pkey" PRIMARY KEY (id);


--
-- Name: deckMatchupProfiles deckMatchupProfiles_pkey; Type: CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckMatchupProfiles"
    ADD CONSTRAINT "deckMatchupProfiles_pkey" PRIMARY KEY (id);


--
-- Name: deckMetrics deckMetrics_pkey; Type: CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckMetrics"
    ADD CONSTRAINT "deckMetrics_pkey" PRIMARY KEY (id);


--
-- Name: deckSnapshots deckSnapshots_pkey; Type: CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckSnapshots"
    ADD CONSTRAINT "deckSnapshots_pkey" PRIMARY KEY (id);


--
-- Name: simulationRuns simulationRuns_pkey; Type: CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."simulationRuns"
    ADD CONSTRAINT "simulationRuns_pkey" PRIMARY KEY (id);


--
-- Name: cardFaces cardFaces_pkey; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."cardFaces"
    ADD CONSTRAINT "cardFaces_pkey" PRIMARY KEY (id);


--
-- Name: cards cards_pkey; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".cards
    ADD CONSTRAINT cards_pkey PRIMARY KEY (id);


--
-- Name: printingImages printingImages_pkey; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."printingImages"
    ADD CONSTRAINT "printingImages_pkey" PRIMARY KEY (id);


--
-- Name: printings printings_pkey; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".printings
    ADD CONSTRAINT printings_pkey PRIMARY KEY (id);


--
-- Name: productContents productContents_pkey; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."productContents"
    ADD CONSTRAINT "productContents_pkey" PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: sets sets_pkey; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".sets
    ADD CONSTRAINT sets_pkey PRIMARY KEY (id);


--
-- Name: printingImages uq_printingImages_printing_face_size; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."printingImages"
    ADD CONSTRAINT "uq_printingImages_printing_face_size" UNIQUE ("printingId", "faceName", "imageSize");


--
-- Name: productContents uq_productContents_product_card_board; Type: CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."productContents"
    ADD CONSTRAINT "uq_productContents_product_card_board" UNIQUE ("productId", "cardId", "boardSection");


--
-- Name: deckCards deckCards_pkey; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckCards"
    ADD CONSTRAINT "deckCards_pkey" PRIMARY KEY (id);


--
-- Name: deckImports deckImports_pkey; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckImports"
    ADD CONSTRAINT "deckImports_pkey" PRIMARY KEY (id);


--
-- Name: deckTags deckTags_pkey; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckTags"
    ADD CONSTRAINT "deckTags_pkey" PRIMARY KEY (id);


--
-- Name: deckVersionCards deckVersionCards_pkey; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersionCards"
    ADD CONSTRAINT "deckVersionCards_pkey" PRIMARY KEY (id);


--
-- Name: deckVersions deckVersions_pkey; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersions"
    ADD CONSTRAINT "deckVersions_pkey" PRIMARY KEY (id);


--
-- Name: decks decks_pkey; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks".decks
    ADD CONSTRAINT decks_pkey PRIMARY KEY (id);


--
-- Name: deckCards uq_deckCards_deck_card_board; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckCards"
    ADD CONSTRAINT "uq_deckCards_deck_card_board" UNIQUE ("deckId", "cardId", "boardType");


--
-- Name: deckVersionCards uq_deckVersionCards_version_card_board; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersionCards"
    ADD CONSTRAINT "uq_deckVersionCards_version_card_board" UNIQUE ("deckVersionId", "cardId", "boardType");


--
-- Name: deckVersions uq_deckVersions_deck_version; Type: CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersions"
    ADD CONSTRAINT "uq_deckVersions_deck_version" UNIQUE ("deckId", "versionNumber");


--
-- Name: branches branches_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".branches
    ADD CONSTRAINT branches_pkey PRIMARY KEY (id);


--
-- Name: cardInstances cardInstances_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances"
    ADD CONSTRAINT "cardInstances_pkey" PRIMARY KEY (id);


--
-- Name: decisions decisions_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".decisions
    ADD CONSTRAINT decisions_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: gamePlayerLibraries gamePlayerLibraries_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayerLibraries"
    ADD CONSTRAINT "gamePlayerLibraries_pkey" PRIMARY KEY (id);


--
-- Name: gamePlayers gamePlayers_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayers"
    ADD CONSTRAINT "gamePlayers_pkey" PRIMARY KEY (id);


--
-- Name: games games_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".games
    ADD CONSTRAINT games_pkey PRIMARY KEY (id);


--
-- Name: stateSnapshots stateSnapshots_pkey; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."stateSnapshots"
    ADD CONSTRAINT "stateSnapshots_pkey" PRIMARY KEY (id);


--
-- Name: events uq_events_game_sequence; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".events
    ADD CONSTRAINT uq_events_game_sequence UNIQUE ("gameId", "sequenceNumber");


--
-- Name: gamePlayers uq_gamePlayers_game_seat; Type: CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayers"
    ADD CONSTRAINT "uq_gamePlayers_game_seat" UNIQUE ("gameId", "seatNumber");


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: ix_cardMatchupTags_cardId_relationType_targetTag; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_cardMatchupTags_cardId_relationType_targetTag" ON "mtgAnalysis"."cardMatchupTags" USING btree ("cardId", "relationType", "targetTag");


--
-- Name: ix_cardRoleTags_cardId_roleType_roleValue; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_cardRoleTags_cardId_roleType_roleValue" ON "mtgAnalysis"."cardRoleTags" USING btree ("cardId", "roleType", "roleValue");


--
-- Name: ix_deckMatchupProfiles_snapshot_archetype; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_deckMatchupProfiles_snapshot_archetype" ON "mtgAnalysis"."deckMatchupProfiles" USING btree ("deckSnapshotId", "archetypeName");


--
-- Name: ix_deckMetrics_snapshot_metricName; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_deckMetrics_snapshot_metricName" ON "mtgAnalysis"."deckMetrics" USING btree ("deckSnapshotId", "metricName");


--
-- Name: ix_mtgAnalysis_archetypes_name; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE UNIQUE INDEX "ix_mtgAnalysis_archetypes_name" ON "mtgAnalysis".archetypes USING btree (name);


--
-- Name: ix_mtgAnalysis_cardMatchupTags_cardId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardMatchupTags_cardId" ON "mtgAnalysis"."cardMatchupTags" USING btree ("cardId");


--
-- Name: ix_mtgAnalysis_cardMatchupTags_relationType; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardMatchupTags_relationType" ON "mtgAnalysis"."cardMatchupTags" USING btree ("relationType");


--
-- Name: ix_mtgAnalysis_cardMatchupTags_source; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardMatchupTags_source" ON "mtgAnalysis"."cardMatchupTags" USING btree (source);


--
-- Name: ix_mtgAnalysis_cardMatchupTags_targetTag; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardMatchupTags_targetTag" ON "mtgAnalysis"."cardMatchupTags" USING btree ("targetTag");


--
-- Name: ix_mtgAnalysis_cardRoleTags_cardId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardRoleTags_cardId" ON "mtgAnalysis"."cardRoleTags" USING btree ("cardId");


--
-- Name: ix_mtgAnalysis_cardRoleTags_roleType; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardRoleTags_roleType" ON "mtgAnalysis"."cardRoleTags" USING btree ("roleType");


--
-- Name: ix_mtgAnalysis_cardRoleTags_roleValue; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardRoleTags_roleValue" ON "mtgAnalysis"."cardRoleTags" USING btree ("roleValue");


--
-- Name: ix_mtgAnalysis_cardRoleTags_source; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_cardRoleTags_source" ON "mtgAnalysis"."cardRoleTags" USING btree (source);


--
-- Name: ix_mtgAnalysis_deckMatchupProfiles_archetypeName; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_deckMatchupProfiles_archetypeName" ON "mtgAnalysis"."deckMatchupProfiles" USING btree ("archetypeName");


--
-- Name: ix_mtgAnalysis_deckMatchupProfiles_deckSnapshotId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_deckMatchupProfiles_deckSnapshotId" ON "mtgAnalysis"."deckMatchupProfiles" USING btree ("deckSnapshotId");


--
-- Name: ix_mtgAnalysis_deckMetrics_deckSnapshotId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_deckMetrics_deckSnapshotId" ON "mtgAnalysis"."deckMetrics" USING btree ("deckSnapshotId");


--
-- Name: ix_mtgAnalysis_deckMetrics_metricGroup; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_deckMetrics_metricGroup" ON "mtgAnalysis"."deckMetrics" USING btree ("metricGroup");


--
-- Name: ix_mtgAnalysis_deckMetrics_metricName; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_deckMetrics_metricName" ON "mtgAnalysis"."deckMetrics" USING btree ("metricName");


--
-- Name: ix_mtgAnalysis_deckSnapshots_deckId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_deckSnapshots_deckId" ON "mtgAnalysis"."deckSnapshots" USING btree ("deckId");


--
-- Name: ix_mtgAnalysis_deckSnapshots_deckVersionId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_deckSnapshots_deckVersionId" ON "mtgAnalysis"."deckSnapshots" USING btree ("deckVersionId");


--
-- Name: ix_mtgAnalysis_simulationRuns_deckId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_simulationRuns_deckId" ON "mtgAnalysis"."simulationRuns" USING btree ("deckId");


--
-- Name: ix_mtgAnalysis_simulationRuns_deckVersionId; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_simulationRuns_deckVersionId" ON "mtgAnalysis"."simulationRuns" USING btree ("deckVersionId");


--
-- Name: ix_mtgAnalysis_simulationRuns_opponentProfile; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_simulationRuns_opponentProfile" ON "mtgAnalysis"."simulationRuns" USING btree ("opponentProfile");


--
-- Name: ix_mtgAnalysis_simulationRuns_runType; Type: INDEX; Schema: mtgAnalysis; Owner: -
--

CREATE INDEX "ix_mtgAnalysis_simulationRuns_runType" ON "mtgAnalysis"."simulationRuns" USING btree ("runType");


--
-- Name: ix_mtgCore_cardFaces_cardId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_cardFaces_cardId" ON "mtgCore"."cardFaces" USING btree ("cardId");


--
-- Name: ix_mtgCore_cards_defaultSetCode; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_cards_defaultSetCode" ON "mtgCore".cards USING btree ("defaultSetCode");


--
-- Name: ix_mtgCore_cards_manaValue; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_cards_manaValue" ON "mtgCore".cards USING btree ("manaValue");


--
-- Name: ix_mtgCore_cards_name; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_cards_name" ON "mtgCore".cards USING btree (name);


--
-- Name: ix_mtgCore_cards_normalizedName; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_cards_normalizedName" ON "mtgCore".cards USING btree ("normalizedName");


--
-- Name: ix_mtgCore_cards_oracleId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_cards_oracleId" ON "mtgCore".cards USING btree ("oracleId");


--
-- Name: ix_mtgCore_cards_uuid; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE UNIQUE INDEX "ix_mtgCore_cards_uuid" ON "mtgCore".cards USING btree (uuid);


--
-- Name: ix_mtgCore_printingImages_faceName; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_printingImages_faceName" ON "mtgCore"."printingImages" USING btree ("faceName");


--
-- Name: ix_mtgCore_printingImages_imageSize; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_printingImages_imageSize" ON "mtgCore"."printingImages" USING btree ("imageSize");


--
-- Name: ix_mtgCore_printingImages_printingId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_printingImages_printingId" ON "mtgCore"."printingImages" USING btree ("printingId");


--
-- Name: ix_mtgCore_printingImages_status; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_printingImages_status" ON "mtgCore"."printingImages" USING btree (status);


--
-- Name: ix_mtgCore_printings_cardId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_printings_cardId" ON "mtgCore".printings USING btree ("cardId");


--
-- Name: ix_mtgCore_printings_rarity; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_printings_rarity" ON "mtgCore".printings USING btree (rarity);


--
-- Name: ix_mtgCore_printings_setId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_printings_setId" ON "mtgCore".printings USING btree ("setId");


--
-- Name: ix_mtgCore_printings_uuid; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE UNIQUE INDEX "ix_mtgCore_printings_uuid" ON "mtgCore".printings USING btree (uuid);


--
-- Name: ix_mtgCore_productContents_cardId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_productContents_cardId" ON "mtgCore"."productContents" USING btree ("cardId");


--
-- Name: ix_mtgCore_productContents_productId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_productContents_productId" ON "mtgCore"."productContents" USING btree ("productId");


--
-- Name: ix_mtgCore_products_name; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_products_name" ON "mtgCore".products USING btree (name);


--
-- Name: ix_mtgCore_products_productCode; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE UNIQUE INDEX "ix_mtgCore_products_productCode" ON "mtgCore".products USING btree ("productCode");


--
-- Name: ix_mtgCore_products_productType; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_products_productType" ON "mtgCore".products USING btree ("productType");


--
-- Name: ix_mtgCore_products_setId; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_products_setId" ON "mtgCore".products USING btree ("setId");


--
-- Name: ix_mtgCore_sets_code; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE UNIQUE INDEX "ix_mtgCore_sets_code" ON "mtgCore".sets USING btree (code);


--
-- Name: ix_mtgCore_sets_name; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_sets_name" ON "mtgCore".sets USING btree (name);


--
-- Name: ix_mtgCore_sets_setType; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_mtgCore_sets_setType" ON "mtgCore".sets USING btree ("setType");


--
-- Name: ix_printingImages_printingId_faceName_imageSize; Type: INDEX; Schema: mtgCore; Owner: -
--

CREATE INDEX "ix_printingImages_printingId_faceName_imageSize" ON "mtgCore"."printingImages" USING btree ("printingId", "faceName", "imageSize");


--
-- Name: ix_deckTags_deckId_tagType_tagValue; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_deckTags_deckId_tagType_tagValue" ON "mtgDecks"."deckTags" USING btree ("deckId", "tagType", "tagValue");


--
-- Name: ix_mtgDecks_deckCards_boardType; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckCards_boardType" ON "mtgDecks"."deckCards" USING btree ("boardType");


--
-- Name: ix_mtgDecks_deckCards_cardId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckCards_cardId" ON "mtgDecks"."deckCards" USING btree ("cardId");


--
-- Name: ix_mtgDecks_deckCards_deckId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckCards_deckId" ON "mtgDecks"."deckCards" USING btree ("deckId");


--
-- Name: ix_mtgDecks_deckCards_preferredPrintingId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckCards_preferredPrintingId" ON "mtgDecks"."deckCards" USING btree ("preferredPrintingId");


--
-- Name: ix_mtgDecks_deckImports_deckId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckImports_deckId" ON "mtgDecks"."deckImports" USING btree ("deckId");


--
-- Name: ix_mtgDecks_deckImports_importSource; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckImports_importSource" ON "mtgDecks"."deckImports" USING btree ("importSource");


--
-- Name: ix_mtgDecks_deckTags_deckId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckTags_deckId" ON "mtgDecks"."deckTags" USING btree ("deckId");


--
-- Name: ix_mtgDecks_deckTags_tagType; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckTags_tagType" ON "mtgDecks"."deckTags" USING btree ("tagType");


--
-- Name: ix_mtgDecks_deckTags_tagValue; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckTags_tagValue" ON "mtgDecks"."deckTags" USING btree ("tagValue");


--
-- Name: ix_mtgDecks_deckVersionCards_cardId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckVersionCards_cardId" ON "mtgDecks"."deckVersionCards" USING btree ("cardId");


--
-- Name: ix_mtgDecks_deckVersionCards_deckVersionId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckVersionCards_deckVersionId" ON "mtgDecks"."deckVersionCards" USING btree ("deckVersionId");


--
-- Name: ix_mtgDecks_deckVersionCards_preferredPrintingId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckVersionCards_preferredPrintingId" ON "mtgDecks"."deckVersionCards" USING btree ("preferredPrintingId");


--
-- Name: ix_mtgDecks_deckVersions_deckId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_deckVersions_deckId" ON "mtgDecks"."deckVersions" USING btree ("deckId");


--
-- Name: ix_mtgDecks_decks_format; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_decks_format" ON "mtgDecks".decks USING btree (format);


--
-- Name: ix_mtgDecks_decks_name; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_decks_name" ON "mtgDecks".decks USING btree (name);


--
-- Name: ix_mtgDecks_decks_ownerUserId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_decks_ownerUserId" ON "mtgDecks".decks USING btree ("ownerUserId");


--
-- Name: ix_mtgDecks_decks_slug; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE UNIQUE INDEX "ix_mtgDecks_decks_slug" ON "mtgDecks".decks USING btree (slug);


--
-- Name: ix_mtgDecks_decks_sourceProductId; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_decks_sourceProductId" ON "mtgDecks".decks USING btree ("sourceProductId");


--
-- Name: ix_mtgDecks_decks_sourceType; Type: INDEX; Schema: mtgDecks; Owner: -
--

CREATE INDEX "ix_mtgDecks_decks_sourceType" ON "mtgDecks".decks USING btree ("sourceType");


--
-- Name: ix_decisions_gameId_sequenceNumber; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_decisions_gameId_sequenceNumber" ON "mtgGames".decisions USING btree ("gameId", "sequenceNumber");


--
-- Name: ix_mtgGames_branches_childGameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE UNIQUE INDEX "ix_mtgGames_branches_childGameId" ON "mtgGames".branches USING btree ("childGameId");


--
-- Name: ix_mtgGames_branches_createdByUserId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_branches_createdByUserId" ON "mtgGames".branches USING btree ("createdByUserId");


--
-- Name: ix_mtgGames_branches_parentGameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_branches_parentGameId" ON "mtgGames".branches USING btree ("parentGameId");


--
-- Name: ix_mtgGames_branches_parentSnapshotId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_branches_parentSnapshotId" ON "mtgGames".branches USING btree ("parentSnapshotId");


--
-- Name: ix_mtgGames_cardInstances_cardId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_cardInstances_cardId" ON "mtgGames"."cardInstances" USING btree ("cardId");


--
-- Name: ix_mtgGames_cardInstances_createdByEventId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_cardInstances_createdByEventId" ON "mtgGames"."cardInstances" USING btree ("createdByEventId");


--
-- Name: ix_mtgGames_cardInstances_gameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_cardInstances_gameId" ON "mtgGames"."cardInstances" USING btree ("gameId");


--
-- Name: ix_mtgGames_cardInstances_gamePlayerId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_cardInstances_gamePlayerId" ON "mtgGames"."cardInstances" USING btree ("gamePlayerId");


--
-- Name: ix_mtgGames_cardInstances_instanceType; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_cardInstances_instanceType" ON "mtgGames"."cardInstances" USING btree ("instanceType");


--
-- Name: ix_mtgGames_cardInstances_printingId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_cardInstances_printingId" ON "mtgGames"."cardInstances" USING btree ("printingId");


--
-- Name: ix_mtgGames_cardInstances_sourceDeckCardId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_cardInstances_sourceDeckCardId" ON "mtgGames"."cardInstances" USING btree ("sourceDeckCardId");


--
-- Name: ix_mtgGames_decisions_actionTakenEventId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_decisions_actionTakenEventId" ON "mtgGames".decisions USING btree ("actionTakenEventId");


--
-- Name: ix_mtgGames_decisions_decisionSource; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_decisions_decisionSource" ON "mtgGames".decisions USING btree ("decisionSource");


--
-- Name: ix_mtgGames_decisions_decisionType; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_decisions_decisionType" ON "mtgGames".decisions USING btree ("decisionType");


--
-- Name: ix_mtgGames_decisions_gameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_decisions_gameId" ON "mtgGames".decisions USING btree ("gameId");


--
-- Name: ix_mtgGames_decisions_gamePlayerId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_decisions_gamePlayerId" ON "mtgGames".decisions USING btree ("gamePlayerId");


--
-- Name: ix_mtgGames_decisions_snapshotId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_decisions_snapshotId" ON "mtgGames".decisions USING btree ("snapshotId");


--
-- Name: ix_mtgGames_events_actingGamePlayerId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_events_actingGamePlayerId" ON "mtgGames".events USING btree ("actingGamePlayerId");


--
-- Name: ix_mtgGames_events_eventType; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_events_eventType" ON "mtgGames".events USING btree ("eventType");


--
-- Name: ix_mtgGames_events_gameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_events_gameId" ON "mtgGames".events USING btree ("gameId");


--
-- Name: ix_mtgGames_events_phase; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_events_phase" ON "mtgGames".events USING btree (phase);


--
-- Name: ix_mtgGames_events_step; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_events_step" ON "mtgGames".events USING btree (step);


--
-- Name: ix_mtgGames_events_turnNumber; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_events_turnNumber" ON "mtgGames".events USING btree ("turnNumber");


--
-- Name: ix_mtgGames_events_visibilityScope; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_events_visibilityScope" ON "mtgGames".events USING btree ("visibilityScope");


--
-- Name: ix_mtgGames_gamePlayerLibraries_gamePlayerId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayerLibraries_gamePlayerId" ON "mtgGames"."gamePlayerLibraries" USING btree ("gamePlayerId");


--
-- Name: ix_mtgGames_gamePlayerLibraries_zoneScope; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayerLibraries_zoneScope" ON "mtgGames"."gamePlayerLibraries" USING btree ("zoneScope");


--
-- Name: ix_mtgGames_gamePlayers_aiProfile; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayers_aiProfile" ON "mtgGames"."gamePlayers" USING btree ("aiProfile");


--
-- Name: ix_mtgGames_gamePlayers_deckId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayers_deckId" ON "mtgGames"."gamePlayers" USING btree ("deckId");


--
-- Name: ix_mtgGames_gamePlayers_deckVersionId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayers_deckVersionId" ON "mtgGames"."gamePlayers" USING btree ("deckVersionId");


--
-- Name: ix_mtgGames_gamePlayers_gameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayers_gameId" ON "mtgGames"."gamePlayers" USING btree ("gameId");


--
-- Name: ix_mtgGames_gamePlayers_playerType; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayers_playerType" ON "mtgGames"."gamePlayers" USING btree ("playerType");


--
-- Name: ix_mtgGames_gamePlayers_result; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayers_result" ON "mtgGames"."gamePlayers" USING btree (result);


--
-- Name: ix_mtgGames_gamePlayers_userId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_gamePlayers_userId" ON "mtgGames"."gamePlayers" USING btree ("userId");


--
-- Name: ix_mtgGames_games_format; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_games_format" ON "mtgGames".games USING btree (format);


--
-- Name: ix_mtgGames_games_gameMode; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_games_gameMode" ON "mtgGames".games USING btree ("gameMode");


--
-- Name: ix_mtgGames_games_parentGameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_games_parentGameId" ON "mtgGames".games USING btree ("parentGameId");


--
-- Name: ix_mtgGames_games_parentSnapshotId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_games_parentSnapshotId" ON "mtgGames".games USING btree ("parentSnapshotId");


--
-- Name: ix_mtgGames_games_rootGameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_games_rootGameId" ON "mtgGames".games USING btree ("rootGameId");


--
-- Name: ix_mtgGames_games_status; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_games_status" ON "mtgGames".games USING btree (status);


--
-- Name: ix_mtgGames_games_winnerGamePlayerId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_games_winnerGamePlayerId" ON "mtgGames".games USING btree ("winnerGamePlayerId");


--
-- Name: ix_mtgGames_stateSnapshots_gameId; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_stateSnapshots_gameId" ON "mtgGames"."stateSnapshots" USING btree ("gameId");


--
-- Name: ix_mtgGames_stateSnapshots_phase; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_stateSnapshots_phase" ON "mtgGames"."stateSnapshots" USING btree (phase);


--
-- Name: ix_mtgGames_stateSnapshots_snapshotHash; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_stateSnapshots_snapshotHash" ON "mtgGames"."stateSnapshots" USING btree ("snapshotHash");


--
-- Name: ix_mtgGames_stateSnapshots_turnNumber; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_mtgGames_stateSnapshots_turnNumber" ON "mtgGames"."stateSnapshots" USING btree ("turnNumber");


--
-- Name: ix_stateSnapshots_gameId_sequenceNumber; Type: INDEX; Schema: mtgGames; Owner: -
--

CREATE INDEX "ix_stateSnapshots_gameId_sequenceNumber" ON "mtgGames"."stateSnapshots" USING btree ("gameId", "sequenceNumber");


--
-- Name: cardMatchupTags cardMatchupTags_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."cardMatchupTags"
    ADD CONSTRAINT "cardMatchupTags_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE CASCADE;


--
-- Name: cardRoleTags cardRoleTags_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."cardRoleTags"
    ADD CONSTRAINT "cardRoleTags_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE CASCADE;


--
-- Name: deckMatchupProfiles deckMatchupProfiles_deckSnapshotId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckMatchupProfiles"
    ADD CONSTRAINT "deckMatchupProfiles_deckSnapshotId_fkey" FOREIGN KEY ("deckSnapshotId") REFERENCES "mtgAnalysis"."deckSnapshots"(id) ON DELETE CASCADE;


--
-- Name: deckMetrics deckMetrics_deckSnapshotId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckMetrics"
    ADD CONSTRAINT "deckMetrics_deckSnapshotId_fkey" FOREIGN KEY ("deckSnapshotId") REFERENCES "mtgAnalysis"."deckSnapshots"(id) ON DELETE CASCADE;


--
-- Name: deckSnapshots deckSnapshots_deckId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckSnapshots"
    ADD CONSTRAINT "deckSnapshots_deckId_fkey" FOREIGN KEY ("deckId") REFERENCES "mtgDecks".decks(id) ON DELETE CASCADE;


--
-- Name: deckSnapshots deckSnapshots_deckVersionId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."deckSnapshots"
    ADD CONSTRAINT "deckSnapshots_deckVersionId_fkey" FOREIGN KEY ("deckVersionId") REFERENCES "mtgDecks"."deckVersions"(id) ON DELETE SET NULL;


--
-- Name: simulationRuns simulationRuns_deckId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."simulationRuns"
    ADD CONSTRAINT "simulationRuns_deckId_fkey" FOREIGN KEY ("deckId") REFERENCES "mtgDecks".decks(id) ON DELETE CASCADE;


--
-- Name: simulationRuns simulationRuns_deckVersionId_fkey; Type: FK CONSTRAINT; Schema: mtgAnalysis; Owner: -
--

ALTER TABLE ONLY "mtgAnalysis"."simulationRuns"
    ADD CONSTRAINT "simulationRuns_deckVersionId_fkey" FOREIGN KEY ("deckVersionId") REFERENCES "mtgDecks"."deckVersions"(id) ON DELETE SET NULL;


--
-- Name: cardFaces cardFaces_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."cardFaces"
    ADD CONSTRAINT "cardFaces_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE CASCADE;


--
-- Name: printingImages printingImages_printingId_fkey; Type: FK CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."printingImages"
    ADD CONSTRAINT "printingImages_printingId_fkey" FOREIGN KEY ("printingId") REFERENCES "mtgCore".printings(id) ON DELETE CASCADE;


--
-- Name: printings printings_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".printings
    ADD CONSTRAINT "printings_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE CASCADE;


--
-- Name: printings printings_setId_fkey; Type: FK CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".printings
    ADD CONSTRAINT "printings_setId_fkey" FOREIGN KEY ("setId") REFERENCES "mtgCore".sets(id) ON DELETE SET NULL;


--
-- Name: productContents productContents_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."productContents"
    ADD CONSTRAINT "productContents_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE CASCADE;


--
-- Name: productContents productContents_productId_fkey; Type: FK CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore"."productContents"
    ADD CONSTRAINT "productContents_productId_fkey" FOREIGN KEY ("productId") REFERENCES "mtgCore".products(id) ON DELETE CASCADE;


--
-- Name: products products_setId_fkey; Type: FK CONSTRAINT; Schema: mtgCore; Owner: -
--

ALTER TABLE ONLY "mtgCore".products
    ADD CONSTRAINT "products_setId_fkey" FOREIGN KEY ("setId") REFERENCES "mtgCore".sets(id) ON DELETE SET NULL;


--
-- Name: deckCards deckCards_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckCards"
    ADD CONSTRAINT "deckCards_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE CASCADE;


--
-- Name: deckCards deckCards_deckId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckCards"
    ADD CONSTRAINT "deckCards_deckId_fkey" FOREIGN KEY ("deckId") REFERENCES "mtgDecks".decks(id) ON DELETE CASCADE;


--
-- Name: deckCards deckCards_preferredPrintingId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckCards"
    ADD CONSTRAINT "deckCards_preferredPrintingId_fkey" FOREIGN KEY ("preferredPrintingId") REFERENCES "mtgCore".printings(id) ON DELETE SET NULL;


--
-- Name: deckImports deckImports_deckId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckImports"
    ADD CONSTRAINT "deckImports_deckId_fkey" FOREIGN KEY ("deckId") REFERENCES "mtgDecks".decks(id) ON DELETE CASCADE;


--
-- Name: deckTags deckTags_deckId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckTags"
    ADD CONSTRAINT "deckTags_deckId_fkey" FOREIGN KEY ("deckId") REFERENCES "mtgDecks".decks(id) ON DELETE CASCADE;


--
-- Name: deckVersionCards deckVersionCards_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersionCards"
    ADD CONSTRAINT "deckVersionCards_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE CASCADE;


--
-- Name: deckVersionCards deckVersionCards_deckVersionId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersionCards"
    ADD CONSTRAINT "deckVersionCards_deckVersionId_fkey" FOREIGN KEY ("deckVersionId") REFERENCES "mtgDecks"."deckVersions"(id) ON DELETE CASCADE;


--
-- Name: deckVersionCards deckVersionCards_preferredPrintingId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersionCards"
    ADD CONSTRAINT "deckVersionCards_preferredPrintingId_fkey" FOREIGN KEY ("preferredPrintingId") REFERENCES "mtgCore".printings(id) ON DELETE SET NULL;


--
-- Name: deckVersions deckVersions_deckId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks"."deckVersions"
    ADD CONSTRAINT "deckVersions_deckId_fkey" FOREIGN KEY ("deckId") REFERENCES "mtgDecks".decks(id) ON DELETE CASCADE;


--
-- Name: decks decks_sourceProductId_fkey; Type: FK CONSTRAINT; Schema: mtgDecks; Owner: -
--

ALTER TABLE ONLY "mtgDecks".decks
    ADD CONSTRAINT "decks_sourceProductId_fkey" FOREIGN KEY ("sourceProductId") REFERENCES "mtgCore".products(id) ON DELETE SET NULL;


--
-- Name: branches branches_childGameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".branches
    ADD CONSTRAINT "branches_childGameId_fkey" FOREIGN KEY ("childGameId") REFERENCES "mtgGames".games(id) ON DELETE CASCADE;


--
-- Name: branches branches_parentGameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".branches
    ADD CONSTRAINT "branches_parentGameId_fkey" FOREIGN KEY ("parentGameId") REFERENCES "mtgGames".games(id) ON DELETE CASCADE;


--
-- Name: branches branches_parentSnapshotId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".branches
    ADD CONSTRAINT "branches_parentSnapshotId_fkey" FOREIGN KEY ("parentSnapshotId") REFERENCES "mtgGames"."stateSnapshots"(id) ON DELETE SET NULL;


--
-- Name: cardInstances cardInstances_cardId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances"
    ADD CONSTRAINT "cardInstances_cardId_fkey" FOREIGN KEY ("cardId") REFERENCES "mtgCore".cards(id) ON DELETE SET NULL;


--
-- Name: cardInstances cardInstances_createdByEventId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances"
    ADD CONSTRAINT "cardInstances_createdByEventId_fkey" FOREIGN KEY ("createdByEventId") REFERENCES "mtgGames".events(id) ON DELETE SET NULL;


--
-- Name: cardInstances cardInstances_gameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances"
    ADD CONSTRAINT "cardInstances_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "mtgGames".games(id) ON DELETE CASCADE;


--
-- Name: cardInstances cardInstances_gamePlayerId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances"
    ADD CONSTRAINT "cardInstances_gamePlayerId_fkey" FOREIGN KEY ("gamePlayerId") REFERENCES "mtgGames"."gamePlayers"(id) ON DELETE SET NULL;


--
-- Name: cardInstances cardInstances_printingId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances"
    ADD CONSTRAINT "cardInstances_printingId_fkey" FOREIGN KEY ("printingId") REFERENCES "mtgCore".printings(id) ON DELETE SET NULL;


--
-- Name: cardInstances cardInstances_sourceDeckCardId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."cardInstances"
    ADD CONSTRAINT "cardInstances_sourceDeckCardId_fkey" FOREIGN KEY ("sourceDeckCardId") REFERENCES "mtgDecks"."deckCards"(id) ON DELETE SET NULL;


--
-- Name: decisions decisions_actionTakenEventId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".decisions
    ADD CONSTRAINT "decisions_actionTakenEventId_fkey" FOREIGN KEY ("actionTakenEventId") REFERENCES "mtgGames".events(id) ON DELETE SET NULL;


--
-- Name: decisions decisions_gameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".decisions
    ADD CONSTRAINT "decisions_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "mtgGames".games(id) ON DELETE CASCADE;


--
-- Name: decisions decisions_gamePlayerId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".decisions
    ADD CONSTRAINT "decisions_gamePlayerId_fkey" FOREIGN KEY ("gamePlayerId") REFERENCES "mtgGames"."gamePlayers"(id) ON DELETE CASCADE;


--
-- Name: decisions decisions_snapshotId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".decisions
    ADD CONSTRAINT "decisions_snapshotId_fkey" FOREIGN KEY ("snapshotId") REFERENCES "mtgGames"."stateSnapshots"(id) ON DELETE SET NULL;


--
-- Name: events events_actingGamePlayerId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".events
    ADD CONSTRAINT "events_actingGamePlayerId_fkey" FOREIGN KEY ("actingGamePlayerId") REFERENCES "mtgGames"."gamePlayers"(id) ON DELETE SET NULL;


--
-- Name: events events_gameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".events
    ADD CONSTRAINT "events_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "mtgGames".games(id) ON DELETE CASCADE;


--
-- Name: gamePlayerLibraries gamePlayerLibraries_gamePlayerId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayerLibraries"
    ADD CONSTRAINT "gamePlayerLibraries_gamePlayerId_fkey" FOREIGN KEY ("gamePlayerId") REFERENCES "mtgGames"."gamePlayers"(id) ON DELETE CASCADE;


--
-- Name: gamePlayers gamePlayers_deckId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayers"
    ADD CONSTRAINT "gamePlayers_deckId_fkey" FOREIGN KEY ("deckId") REFERENCES "mtgDecks".decks(id) ON DELETE SET NULL;


--
-- Name: gamePlayers gamePlayers_deckVersionId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayers"
    ADD CONSTRAINT "gamePlayers_deckVersionId_fkey" FOREIGN KEY ("deckVersionId") REFERENCES "mtgDecks"."deckVersions"(id) ON DELETE SET NULL;


--
-- Name: gamePlayers gamePlayers_gameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."gamePlayers"
    ADD CONSTRAINT "gamePlayers_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "mtgGames".games(id) ON DELETE CASCADE;


--
-- Name: games games_parentGameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".games
    ADD CONSTRAINT "games_parentGameId_fkey" FOREIGN KEY ("parentGameId") REFERENCES "mtgGames".games(id) ON DELETE SET NULL;


--
-- Name: games games_parentSnapshotId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".games
    ADD CONSTRAINT "games_parentSnapshotId_fkey" FOREIGN KEY ("parentSnapshotId") REFERENCES "mtgGames"."stateSnapshots"(id) ON DELETE SET NULL;


--
-- Name: games games_winnerGamePlayerId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames".games
    ADD CONSTRAINT "games_winnerGamePlayerId_fkey" FOREIGN KEY ("winnerGamePlayerId") REFERENCES "mtgGames"."gamePlayers"(id) ON DELETE SET NULL;


--
-- Name: stateSnapshots stateSnapshots_gameId_fkey; Type: FK CONSTRAINT; Schema: mtgGames; Owner: -
--

ALTER TABLE ONLY "mtgGames"."stateSnapshots"
    ADD CONSTRAINT "stateSnapshots_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "mtgGames".games(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict NeU155LuQOEyKNQlQXlHepProYhUjwUe8CcGTGSgtzRN7UV1uak65anqJ49fxqq

