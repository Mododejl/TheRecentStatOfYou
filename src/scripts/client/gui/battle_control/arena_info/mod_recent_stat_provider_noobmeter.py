# -*- coding: utf-8 -*-
# https://www.apache.org/licenses/LICENSE-2.0.html

import traceback

from mod_recent_stat_constant import PLAYER_ID_NOT_KNOWN, COLUMN_ID_NOT_FOUND, MAX_ITERATIONS
from mod_recent_stat_logging import logInfo, logError
from mod_recent_stat_network import getSiteText, getNextRowCells, getNumberFromCell


def getPlayerId(idSiteText, nickname):
    try:
        nameTitle = "<h1>%s</h1>" % nickname
        nameTitleEndIndex = idSiteText.find(nameTitle) + len(nameTitle)
        idStartIndex = idSiteText.find("<!--", nameTitleEndIndex) + len("<!--")
        idEndIndex = idSiteText.find("-->", idStartIndex) - 1
        return int(idSiteText[idStartIndex:idEndIndex].strip())
    except BaseException:
        logError("Can't get id from text", traceback.format_exc())
        return PLAYER_ID_NOT_KNOWN


def _getStatTableBeginIdx(siteText):
    iterations = 0

    tableBeginIdx = 0
    while True:
        tableBeginIdx = siteText.find("<table", tableBeginIdx + 1)
        classBeginIdx = siteText.find("tablesorter", tableBeginIdx)
        endTableBeginIdx = siteText.find(">", tableBeginIdx)
        if classBeginIdx < endTableBeginIdx:
            break

        assert iterations < MAX_ITERATIONS, "Too many iterations: %s" % iterations
        iterations += 1

    return tableBeginIdx


def _getOverallAndRecentColumnIdx(siteText, tableBeginIdx):
    ths = getNextRowCells(siteText, tableBeginIdx, "th")

    overallColumnIdx = COLUMN_ID_NOT_FOUND
    recentColumnIdx = COLUMN_ID_NOT_FOUND

    for i, th in reversed(tuple(enumerate(ths))):
        if "Общий" in th or "Overall" in th:
            overallColumnIdx = i
        if "~1000" in th or "~1,000" in th:
            recentColumnIdx = i

    assert overallColumnIdx != COLUMN_ID_NOT_FOUND, "No overall column found in %s" % ths

    return overallColumnIdx, recentColumnIdx


def _getTrsWithData(siteText, tableBeginIdx):
    iterations = 0

    headerEndIdx = siteText.find("</tr>", tableBeginIdx)
    tableEndIdx = siteText.find("</table>", headerEndIdx)
    nextTrBeginIdx = headerEndIdx

    trs = list()

    while nextTrBeginIdx != -1 and nextTrBeginIdx < tableEndIdx:
        nowTrBeginIdx = nextTrBeginIdx

        tds = getNextRowCells(siteText, nowTrBeginIdx)
        trs.append(tds)

        nextTrBeginIdx = siteText.find("<tr", nowTrBeginIdx + 1)

        assert iterations < MAX_ITERATIONS, "Too many iterations: %s" % iterations
        iterations += 1

    return trs


def getStatistics(region, nickname, playerId):
    if playerId == PLAYER_ID_NOT_KNOWN:
        idSiteText = getSiteText("http://www.noobmeter.com/player/%s/%s" % (region, nickname))
        playerId = getPlayerId(idSiteText, nickname)
        logInfo("Player ID of %s = %s" % (nickname, playerId))

    siteText = getSiteText("http://www.noobmeter.com/player/%s/%s/%d" % (region, nickname, playerId))

    try:
        tableBeginIdx = _getStatTableBeginIdx(siteText)
        overallColumnIdx, recentColumnIdx = _getOverallAndRecentColumnIdx(siteText, tableBeginIdx)
        trs = _getTrsWithData(siteText, tableBeginIdx)

        wn8 = ""
        battlesRecent = None
        battlesOverall = ""

        for tds in trs:
            if len(tds) != 0:
                loweredRowTitle = tds[0].lower()

                if "wn8" in loweredRowTitle:
                    if recentColumnIdx != -1:
                        wn8ParsedStr = getNumberFromCell(tds[recentColumnIdx])
                    else:
                        wn8ParsedStr = getNumberFromCell(tds[overallColumnIdx])

                    if wn8ParsedStr is not None:
                        wn8 = wn8ParsedStr
                elif "battles:" in loweredRowTitle or "кол. боёв:" in loweredRowTitle:
                    if recentColumnIdx != -1:
                        battlesRecent = getNumberFromCell(tds[recentColumnIdx])

                    battlesOverall = getNumberFromCell(tds[overallColumnIdx])

        playerStat = wn8 + "["
        if battlesRecent is not None:
            playerStat += battlesRecent + "/"
        playerStat += str(int(round(int(battlesOverall) / 1000.0))) + "k]"

        return playerStat
    except BaseException:
        logError("Error in getStatistics(%s, %s, %s)" % (region, nickname, playerId), traceback.format_exc())
        return "[?-?]"
