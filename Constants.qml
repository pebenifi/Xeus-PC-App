import QtQuick

pragma Singleton

QtObject {
    readonly property int width: 1920
    readonly property int height: 1080
    readonly property int minWidth: 1920
    readonly property int minHeight: 1080

    // Font family - fixed to Arial for consistency
    readonly property string fontFamily: "Arial"
    
    // Colors
    readonly property color colorWhite: "#ffffff"
    readonly property color colorBlack: "#000000"
    readonly property color colorDarkBlue: "#293555"
    readonly property color colorGrey: "#979797"
    readonly property color colorDarkGreen: "#38691e"
    readonly property color colorLightGrey: "#fafafa"
    readonly property color colorTextGrey: "#666666" // Added for parameter labels
    
    // Specific element colors
    readonly property color buttonText: "#ffffff"
    readonly property color labelText: "#ffffff" // For text on dark backgrounds
    readonly property color labelTextDark: "#000000" // For text on white backgrounds
    
    // Font definitions (Fixed pixel sizes to ensure consistency across screens with appScaler)
    // Converted point sizes to pixels based on standard 96 DPI (1pt = 1.33px)
    
    // Originally pointSize: 22 (~29px)
    property var fontMediumPt: Qt.font({
        family: fontFamily,
        pixelSize: 29,
        bold: false
    })
    
    // Originally pointSize: 24 (~32px)
    property var fontLargePt: Qt.font({
        family: fontFamily,
        pixelSize: 32,
        bold: false
    })
    
    // Originally pixelSize: 30
    property var fontHugePx: Qt.font({
        family: fontFamily,
        pixelSize: 30,
        bold: false
    })

    // Originally pixelSize: 24
    property var fontLargePx: Qt.font({
        family: fontFamily,
        pixelSize: 24,
        bold: false
    })

    // Originally pixelSize: 22
    property var fontMediumPx: Qt.font({
        family: fontFamily,
        pixelSize: 22,
        bold: false
    })

    // Originally pixelSize: 20
    property var fontSmallPx: Qt.font({
        family: fontFamily,
        pixelSize: 20,
        bold: false
    })

    // Originally pixelSize: 15
    property var fontTinyPx: Qt.font({
        family: fontFamily,
        pixelSize: 15,
        bold: false
    })

    // New fonts for parameter lists (based on Clinicalmode.qml analysis)
    // Originally pixelSize: 18 (bold)
    property var fontHeaderPx: Qt.font({
        family: fontFamily,
        pixelSize: 18,
        bold: true
    })

    // Originally pixelSize: 14
    property var fontSubHeaderPx: Qt.font({
        family: fontFamily,
        pixelSize: 14,
        bold: false
    })

    // Originally pixelSize: 13
    property var fontBodyPx: Qt.font({
        family: fontFamily,
        pixelSize: 13,
        bold: false
    })

    // Originally pixelSize: 12
    property var fontDetailPx: Qt.font({
        family: fontFamily,
        pixelSize: 12,
        bold: false
    })

    // Originally pixelSize: 12 (bold)
    property var fontDetailBoldPx: Qt.font({
        family: fontFamily,
        pixelSize: 12,
        bold: true
    })
    
    // Originally pixelSize: 11
    property var fontMicroPx: Qt.font({
        family: fontFamily,
        pixelSize: 11,
        bold: false
    })

    // Originally pixelSize: 11 (bold)
    property var fontMicroBoldPx: Qt.font({
        family: fontFamily,
        pixelSize: 11,
        bold: true
    })

    // Originally pixelSize: 10
    property var fontNanoPx: Qt.font({
        family: fontFamily,
        pixelSize: 10,
        bold: false
    })

    // New smaller font for buttons (requested by user)
    // Reduced to 14px for "buttons on the right and disconnect"
    // Updated to 16px per user request
    property var fontButtonSmallPx: Qt.font({
        family: fontFamily,
        pixelSize: 16,
        bold: false
    })
}
