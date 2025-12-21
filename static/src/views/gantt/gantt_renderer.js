import {
    diffColumn,
    localEndOf,
    localStartOf,
    datePlus,
    dateMinus,
    getRangeFromDate,
} from "./gantt_helpers";
import { _t } from "@web/core/l10n/translation";
import { GanttRenderer } from "@web_gantt/gantt_renderer";
import { patch } from "@web/core/utils/patch";
const { DateTime, Interval } = luxon;

patch(GanttRenderer.prototype, {
    /**
     * @override
     */
   setup() {
        super.setup();
        const { slotMinTime, slotMaxTime } = this.model.metaData;
        this.hideNonBusinessHours =  (slotMinTime && slotMaxTime) ? true : false;
    },
    computeDerivedParams() {
        const { scale } = this.model.metaData;
        const { interval } = scale;
        super.computeDerivedParams();
        if( this.hideNonBusinessHours && interval === 'hour'){
            const { globalStart, globalStop, startDate, stopDate } = this.model.metaData;
            const globalStartDate = localStartOf(globalStart, interval, this.model.metaData);
            const globalStopDate = localStartOf(globalStop, interval, this.model.metaData);

            this.columnCount = diffColumn(globalStartDate, globalStopDate, interval, this.model.metaData);

            this.model.metaData.globalStart = globalStartDate;
            this.model.metaData.globalStop = globalStopDate;
            this.model.metaData.startDate = localStartOf(startDate, interval, this.model.metaData);
            this.model.metaData.stopDate = localStartOf(stopDate, interval, this.model.metaData);
        } 
    },
    computeVisibleColumns() {
        const { scale } = this.model.metaData;
        if(!this.hideNonBusinessHours || scale.interval != 'hour'){
            super.computeVisibleColumns();
        } else {
            const [firstIndex, lastIndex] = this.virtualGrid.columnsIndexes;
            this.columnsGroups = [];
            this.columns = [];
            this.subColumns = [];
            this.coarseGridCols = {
                1: true,
                [this.columnCount * this.model.metaData.scale.cellPart + 1]: true,
            };
            const { globalStart, globalStop } = this.model.metaData;
            const { cellPart, interval, unit } = scale;

            const now = DateTime.local();

            const nowStart = now.startOf(interval);
            const nowEnd = now.endOf(interval);

            const groupsLeftBound = DateTime.max(
                globalStart,
                localStartOf(datePlus(globalStart, firstIndex, interval, this.model.metaData), unit, this.model.metaData)
            );
            const groupsRightBound = DateTime.min(
                localEndOf(datePlus(globalStart, lastIndex, interval, this.model.metaData), unit, this.model.metaData),
                globalStop
            );
            let currentGroup = null;
            for (let j = firstIndex; j <= lastIndex; j++) {
                const columnId = `__column__${j + 1}`;
                const col = j * cellPart + 1;
                const { start, stop } = this.getColumnFromColNumber(col);
                const column = {
                    id: columnId,
                    grid: { column: [col, col + cellPart] },
                    start,
                    stop,
                };
                const isToday = nowStart <= start && start <= nowEnd;
                const isPast = start < nowStart;
                if (isToday) {
                    column.isToday = true;
                }
                if (isPast) {
                    column.isPast = true;
                }   
                this.columns.push(column);

                for (let i = 0; i < cellPart; i++) {
                    const subColumn = this.getSubColumnFromColNumber(col + i);
                    this.subColumns.push({ ...subColumn, isToday, isPast, columnId });
                    this.coarseGridCols[col + i] = true;
                }

                const groupStart = localStartOf(start, unit, this.model.metaData);
                if (!currentGroup || !groupStart.equals(currentGroup.start)) {
                    const groupId = `__group__${this.columnsGroups.length + 1}`;
                    const startingBound = DateTime.max(groupsLeftBound, groupStart);
                    const endingBound = DateTime.min(groupsRightBound, localEndOf(groupStart, unit, this.model.metaData));
                    const [groupFirstCol, groupLastCol] = this.getGridColumnFromDates(
                        startingBound,
                        endingBound
                    );
                    currentGroup = {
                        id: groupId,
                        grid: { column: [groupFirstCol, groupLastCol] },
                        start: groupStart,
                    };
                    this.columnsGroups.push(currentGroup);
                    this.coarseGridCols[groupFirstCol] = true;
                    this.coarseGridCols[groupLastCol] = true;
                }
            }
        }
    },
    getColumnFromColNumber(col) {
        let column;
        const { scale } = this.model.metaData;
        if(!this.hideNonBusinessHours || scale.interval !== 'hour'){
            column = super.getColumnFromColNumber(col);
        } else {
            column = this.mappingColToColumn.get(col);
            if (!column) {
                const { globalStart } = this.model.metaData;
                const { interval, cellPart } = scale;
                const delta = (col - 1) % cellPart;
                const columnIndex = ((col - 1 - delta) / cellPart);
                const start = datePlus(globalStart, columnIndex, interval, this.model.metaData);
                const stop = start.endOf(interval);
                column = { start, stop };
                this.mappingColToColumn.set(col, column);
            }
        }
        return column;
    },
    getSubColumnFromColNumber(col) {
        let subColumn;
        const { scale } = this.model.metaData;
        if(!this.hideNonBusinessHours || scale.interval !== 'hour' ){
            subColumn = super.getSubColumnFromColNumber(col);
        } else {
            subColumn = this.mappingColToColumn.get(col);
            if (!subColumn) {
                const { globalStart } = this.model.metaData;
                const { interval, cellPart, cellTime, time } = scale;
                const delta = (col - 1) % cellPart;
                const columnIndex = ((col - 1 - delta) / cellPart);
                const start = datePlus(globalStart, columnIndex, interval, this.model.metaData);
                subColumn = this.makeSubColumn(start, delta, cellTime, time);
                this.mappingColToSubColumn.set(col, subColumn);
            }
        }
        return subColumn;
    },
    getGridColumnFromDates(startDate, stopDate) {
        const { scale } = this.model.metaData;
        if(!this.hideNonBusinessHours || scale.interval !== 'hour'){
            return super.getGridColumnFromDates(startDate, stopDate);
        } else {
            const { globalStart } = this.model.metaData;
            const { cellPart, interval } = scale;
            const { column: column1, delta: delta1 } = this.getSubColumnFromDate(startDate);
            const { column: column2, delta: delta2 } = this.getSubColumnFromDate(stopDate, false);
            const firstCol = 1 + diffColumn(globalStart, column1, interval, this.model.metaData) * cellPart + delta1;
            const span = diffColumn(column1, column2, interval, this.model.metaData) * cellPart + delta2 - delta1;
            return [firstCol, firstCol + span];
        }
    },
    ganttCellAttClass(row, column) {
        return {
            o_sample_data_disabled: this.isDisabled(row),
            o_gantt_today: column.isToday,
            o_appointment_booking_gantt_color_grey: column.isPast,
            o_gantt_group: row.isGroup,
            o_gantt_hoverable: this.isHoverable(row),
            o_group_open: !this.model.isClosed(row.id),
            o_gantt_readonly: row.readonly,
        };
    },
});
