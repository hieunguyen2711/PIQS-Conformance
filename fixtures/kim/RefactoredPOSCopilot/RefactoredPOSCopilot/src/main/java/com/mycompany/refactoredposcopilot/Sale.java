/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredposcopilot;

import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.List;

/**
 *
 * @author kim2
 */
// Composite Pattern for Sale and SaleLineItem
class Sale {
    private DecimalFormat dfMoney = new DecimalFormat("$##.00");
    private List<SaleLineItem> slis = new ArrayList<>();

    public List<SaleLineItem> getSaleLineItem() {
        return slis;
    }

    public void add(SaleLineItem sli) {
        slis.add(sli);
        System.out.println("• "+sli.getItemName()+ "\t" + sli.getQuantity() + "\t\t" + dfMoney.format(sli.getSubTotal()));
    }
}
