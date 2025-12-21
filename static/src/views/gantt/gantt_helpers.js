import { useService } from "@web/core/utils/hooks";
import * as gantt_helpers from "@web_gantt/gantt_helpers";
const { DateTime } = luxon;

/** @typedef {luxon.DateTime} DateTime */

export function diffColumn(col1, col2, unit, metaData) {
        let result = 0;
        const { slotMaxTime, slotMinTime } = metaData;
        if(!slotMinTime || !slotMaxTime || unit != 'hour'){
            result = gantt_helpers.diffColumn(col1, col2, unit);
        } else {
            const open = slotMinTime;
            const close = slotMaxTime;

            let current = col1;

            while (current < col2) {
                // If today is a business day
                // Get start and end of business hours for today
                const startDate = current.set({ 
                    hour: parseInt(open.split(":")[0], 10), 
                    minute: parseInt(open.split(":")[1], 10), 
                    second: 0 
                });
                const stopDate = current.set({ 
                    hour: parseInt(close.split(":")[0], 10), 
                    minute: parseInt(close.split(":")[1], 10), 
                    second: 0 
                });

                // Find overlap with current day
                const intervalStart = current > startDate ? current : startDate;
                const intervalEnd = col2 < stopDate ? col2 : stopDate;

                if (intervalStart < intervalEnd) {
                    result += intervalEnd.diff(intervalStart, unit).hours;
                }
                // Move to next day at midnight
                current = current.plus({ days: 1 }).startOf('day');
            }
        }
        return result;
}

export function getRangeFromDate(rangeId, date, metaData) {
    const startDate = localStartOf(date, rangeId, metaData);
    const stopDate = dateMinus(datePlus(startDate, 1, rangeId, metaData), 1, "day", metaData);
    return { focusDate: date, startDate, stopDate, rangeId };
}

export function localStartOf(date, unit, metaData) {
    let resultDate = gantt_helpers.localStartOf(date,unit);
    const { slotMinTime, slotMaxTime, scale } = metaData;
    if(slotMinTime && slotMaxTime && scale.interval === 'hour'){
        resultDate =  resultDate.set({
                            hour: parseInt(slotMinTime.split(":")[0], 10),  
                            minute: parseInt(slotMinTime.split(":")[1], 10),
                            second: 0,
                            millisecond: 0, 
                        });
    }
    return resultDate;
}

export function localEndOf(date, unit, metaData) {
    const { slotMinTime, slotMaxTime, scale } = metaData
    let resultDate = gantt_helpers.localEndOf(date,unit);
    if(slotMinTime && slotMaxTime && scale.interval === 'hour'){
        resultDate = resultDate.set({
                        hour: parseInt(slotMaxTime.split(":")[0], 10),  
                        minute: parseInt(slotMaxTime.split(":")[1], 10),
                        second: 0,
                        millisecond: 0, 
                        });
    }
    return resultDate;
}

export function datePlus(startDate, intervalToAdd, interval='hour', metaData) {
    const { slotMinTime, slotMaxTime } = metaData;
    if(!slotMinTime || !slotMaxTime || interval !== 'hour'){
        return startDate.plus({[interval]: intervalToAdd});
    } else {
        const openTimeString = slotMinTime;
        const closeTimeString = slotMaxTime;
        const openDateTime = DateTime.fromFormat(openTimeString, 'HH:mm');
        const closeDateTime = DateTime.fromFormat(closeTimeString, 'HH:mm');

        let hoursRemaining = intervalToAdd;
        let result = startDate;

        while (hoursRemaining > 0) {
            let currentHour = result.hour;
            // If before business start, move to business start
            if (currentHour < openDateTime.hour) {
                result = result.set({
                    hour: parseInt(openTimeString.split(":")[0], 10), 
                    minute: parseInt(openTimeString.split(":")[1], 10), 
                    second: 0, 
                    millisecond: 0
                });
                currentHour = openDateTime.hour;
            } else if (currentHour >= parseInt(close)) {
                result = result.plus({days: 1}).set({
                    hour: parseInt(openTimeString.split(":")[0], 10), 
                    minute: parseInt(openTimeString.split(":")[1], 10), 
                    second: 0, 
                    millisecond: 0
                });
                continue;
            }
            // Remaining hours in today's business window
            let hoursInDay = closeDateTime.hour - currentHour;
            let useHours = Math.min(hoursInDay, hoursRemaining);
            result = result.plus({hours: useHours});
            hoursRemaining -= useHours;
            // If we finished within today's window, return
            if (hoursRemaining <= 0) break;

            // Otherwise, move to next day at business start hour
            result = result.plus({days: 1}).set({
                hour: parseInt(openTimeString.split(":")[0], 10), 
                minute: parseInt(openTimeString.split(":")[1], 10), 
                millisecond: 0
            });
        }
        if(result.hour == closeDateTime.hour){
            result = result.plus({days: 1}).set({
                hour: parseInt(openTimeString.split(":")[0], 10), 
                minute: parseInt(openTimeString.split(":")[1], 10), 
                millisecond: 0
            });
        }
        return result;
    }
}

export function dateMinus(startDate, intervalToSubtract, interval='hour', metaData) {
    const { slotMinTime, slotMaxTime } = metaData;
    if(!slotMinTime || !slotMaxTime || interval !== 'hour'){
        return startDate.minus({[interval]: intervalToSubtract});
    } else {
        const openTimeString = slotMinTime;
        const closeTimeString = slotMaxTime;
        const openDateTime = DateTime.fromFormat(openTimeString, 'HH:mm');
        const closeDateTime = DateTime.fromFormat(closeTimeString, 'HH:mm');

        let hoursRemaining = intervalToSubtract;
        let result = startDate;

        while (hoursRemaining > 0) {
            let currentHour = result.hour;
            
            // If at or after business close, move to previous day's business close
            if (currentHour >= closeDateTime.hour) {
                result = result.minus({days: 1}).set({
                    hour: parseInt(closeTimeString.split(":")[0], 10), 
                    minute: parseInt(closeTimeString.split(":")[1], 10), 
                    second: 0, 
                    millisecond: 0
                });
                currentHour = closeDateTime.hour;
            } else if (currentHour < openDateTime.hour) {
                // Already before open, but shouldn't happen in normal flow
                result = result.minus({days: 1}).set({
                    hour: parseInt(closeTimeString.split(":")[0], 10), 
                    minute: parseInt(closeTimeString.split(":")[1], 10), 
                    second: 0, 
                    millisecond: 0
                });
                continue;
            }
            
            // Remaining hours in today's business window (from open to current)
            let hoursInDay = currentHour - openDateTime.hour;
            let useHours = Math.min(hoursInDay, hoursRemaining);
            result = result.minus({hours: useHours});
            hoursRemaining -= useHours;
            
            // If we finished within today's window, return
            if (hoursRemaining <= 0) break;

            // Otherwise, move to previous day at business close hour
            result = result.minus({days: 1}).set({
                hour: parseInt(closeTimeString.split(":")[0], 10), 
                minute: parseInt(closeTimeString.split(":")[1], 10), 
                second: 0, 
                millisecond: 0
            });
        }
        
        // Ensure we don't land exactly on business close time (move to previous day open)
        if(result.hour >= closeDateTime.hour){
            result = result.minus({days: 1}).set({
                hour: parseInt(openTimeString.split(":")[0], 10), 
                minute: parseInt(openTimeString.split(":")[1], 10), 
                second: 0, 
                millisecond: 0
            });
        }
        
        return result;
    }
}
