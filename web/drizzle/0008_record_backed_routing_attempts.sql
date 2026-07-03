ALTER TABLE `routing_attempts`
	MODIFY COLUMN `documentId` int;
--> statement-breakpoint
ALTER TABLE `routing_attempts`
	ADD COLUMN `bookkeepingRecordId` int;
--> statement-breakpoint
CREATE INDEX `idx_routing_bookkeeping_record`
	ON `routing_attempts` (`bookkeepingRecordId`);
