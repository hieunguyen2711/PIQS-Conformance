/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsmeta;

import java.util.Observable;

/**
 *
 * @author kim2
 */
// AuditLog class with Observer pattern
class AuditLog extends Observable {
    public void logAction(String logEntry) {
        setChanged();
        notifyObservers(logEntry);
    }
}
