CREATE TABLE `bookkeeping_documents` (
	`id` int AUTO_INCREMENT NOT NULL,
	`source` varchar(64) NOT NULL,
	`sourceDocumentId` varchar(255),
	`originalFilename` varchar(500) NOT NULL,
	`mimeType` varchar(120),
	`storagePath` varchar(1000),
	`documentType` enum('receipt','invoice','order_confirmation','bank_transaction','statement','unknown') NOT NULL DEFAULT 'unknown',
	`processingStatus` enum('imported','processing','extracted','validated','needs_review','approved','routed','reconciled','failed','archived') NOT NULL DEFAULT 'imported',
	`duplicateFingerprint` varchar(128),
	`duplicateOfDocumentId` int,
	`vendorName` varchar(255),
	`category` varchar(255),
	`transactionDate` date,
	`totalAmount` decimal(12,2),
	`vatAmount` decimal(12,2),
	`confidenceScore` decimal(5,4),
	`ocrText` text,
	`extractedData` json,
	`metadata` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `bookkeeping_documents_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `vendors` (
	`id` int AUTO_INCREMENT NOT NULL,
	`name` varchar(255) NOT NULL,
	`normalizedName` varchar(255) NOT NULL,
	`defaultCategory` varchar(255),
	`aliases` json,
	`metadata` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `vendors_id` PRIMARY KEY(`id`),
	CONSTRAINT `vendors_name_unique` UNIQUE(`name`)
);
--> statement-breakpoint
CREATE TABLE `categories` (
	`id` int AUTO_INCREMENT NOT NULL,
	`name` varchar(255) NOT NULL,
	`parentId` int,
	`routeTarget` enum('mijngeldzaken','waveapps_business','waveapps_personal','manual_review','none') NOT NULL DEFAULT 'manual_review',
	`rules` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `categories_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `review_items` (
	`id` int AUTO_INCREMENT NOT NULL,
	`documentId` int,
	`reason` varchar(120) NOT NULL,
	`details` text,
	`status` enum('pending','in_review','approved','rejected','resolved') NOT NULL DEFAULT 'pending',
	`assignedToUserId` int,
	`resolution` text,
	`correctedData` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	`resolvedAt` timestamp,
	CONSTRAINT `review_items_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `workflow_runs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`status` enum('queued','running','completed','completed_with_review','failed','cancelled') NOT NULL DEFAULT 'queued',
	`triggerSource` varchar(100) NOT NULL DEFAULT 'manual',
	`documentsImported` int NOT NULL DEFAULT 0,
	`documentsProcessed` int NOT NULL DEFAULT 0,
	`documentsNeedingReview` int NOT NULL DEFAULT 0,
	`errorMessage` text,
	`startedAt` timestamp,
	`finishedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`metadata` json,
	CONSTRAINT `workflow_runs_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `routing_attempts` (
	`id` int AUTO_INCREMENT NOT NULL,
	`documentId` int NOT NULL,
	`workflowRunId` int,
	`target` enum('mijngeldzaken','waveapps_business','waveapps_personal','manual_review','none') NOT NULL,
	`status` enum('pending','submitted','success','failed','skipped','requires_review') NOT NULL DEFAULT 'pending',
	`externalId` varchar(255),
	`message` text,
	`attemptedAt` timestamp NOT NULL DEFAULT (now()),
	`metadata` json,
	CONSTRAINT `routing_attempts_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `reconciliation_matches` (
	`id` int AUTO_INCREMENT NOT NULL,
	`documentId` int,
	`bankTransactionId` varchar(255) NOT NULL,
	`status` enum('matched','unmatched','partial','review') NOT NULL DEFAULT 'review',
	`confidenceScore` decimal(5,4),
	`amountDifference` decimal(12,2),
	`matchedAt` timestamp,
	`metadata` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `reconciliation_matches_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `audit_events` (
	`id` int AUTO_INCREMENT NOT NULL,
	`actorUserId` int,
	`action` varchar(120) NOT NULL,
	`entityType` varchar(80) NOT NULL,
	`entityId` varchar(120),
	`details` json,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `audit_events_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE INDEX `idx_bookkeeping_docs_status` ON `bookkeeping_documents` (`processingStatus`);
--> statement-breakpoint
CREATE INDEX `idx_bookkeeping_docs_source` ON `bookkeeping_documents` (`source`,`sourceDocumentId`);
--> statement-breakpoint
CREATE INDEX `idx_bookkeeping_docs_vendor` ON `bookkeeping_documents` (`vendorName`);
--> statement-breakpoint
CREATE INDEX `idx_bookkeeping_docs_category` ON `bookkeeping_documents` (`category`);
--> statement-breakpoint
CREATE INDEX `idx_bookkeeping_docs_date` ON `bookkeeping_documents` (`transactionDate`);
--> statement-breakpoint
CREATE INDEX `idx_bookkeeping_docs_fingerprint` ON `bookkeeping_documents` (`duplicateFingerprint`);
--> statement-breakpoint
CREATE INDEX `idx_vendors_normalized` ON `vendors` (`normalizedName`);
--> statement-breakpoint
CREATE INDEX `idx_vendors_category` ON `vendors` (`defaultCategory`);
--> statement-breakpoint
CREATE INDEX `idx_categories_parent` ON `categories` (`parentId`);
--> statement-breakpoint
CREATE INDEX `idx_categories_route` ON `categories` (`routeTarget`);
--> statement-breakpoint
CREATE INDEX `idx_review_status` ON `review_items` (`status`);
--> statement-breakpoint
CREATE INDEX `idx_review_document` ON `review_items` (`documentId`);
--> statement-breakpoint
CREATE INDEX `idx_review_assignee` ON `review_items` (`assignedToUserId`);
--> statement-breakpoint
CREATE INDEX `idx_review_created` ON `review_items` (`createdAt`);
--> statement-breakpoint
CREATE INDEX `idx_workflow_status` ON `workflow_runs` (`status`);
--> statement-breakpoint
CREATE INDEX `idx_workflow_created` ON `workflow_runs` (`createdAt`);
--> statement-breakpoint
CREATE INDEX `idx_routing_document` ON `routing_attempts` (`documentId`);
--> statement-breakpoint
CREATE INDEX `idx_routing_workflow` ON `routing_attempts` (`workflowRunId`);
--> statement-breakpoint
CREATE INDEX `idx_routing_target_status` ON `routing_attempts` (`target`,`status`);
--> statement-breakpoint
CREATE INDEX `idx_reconciliation_document` ON `reconciliation_matches` (`documentId`);
--> statement-breakpoint
CREATE INDEX `idx_reconciliation_status` ON `reconciliation_matches` (`status`);
--> statement-breakpoint
CREATE INDEX `idx_reconciliation_bank_tx` ON `reconciliation_matches` (`bankTransactionId`);
--> statement-breakpoint
CREATE INDEX `idx_audit_actor` ON `audit_events` (`actorUserId`);
--> statement-breakpoint
CREATE INDEX `idx_audit_entity` ON `audit_events` (`entityType`,`entityId`);
--> statement-breakpoint
CREATE INDEX `idx_audit_created` ON `audit_events` (`createdAt`);
